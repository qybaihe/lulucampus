"""Campus MCP: whitelist tools over HTTP, bound to a Redis tool_session.

The sidecar Agent may only call these tools. Commit / --confirm actions are
never registered. Write tools return a preview payload; the user still confirms
via /actions/preview → /actions/execute.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.database import SessionLocal
from onemore.core.errors import AppError
from onemore.db.models import AuthorizationGrant
from onemore.hermes.catalog import CATALOG, ActionTier
from onemore.hermes.schemas import ActionName
from onemore.modules.actions import service as action_service

logger = logging.getLogger("onemore.hermes.campus_mcp")

SESSION_KEY_PREFIX = "onemore:hermes:tool_session:"
FORBIDDEN_TOOL_MARKERS = ("_commit", "commit", "--confirm")

CardKind = Literal[
    "course_list",
    "assignment_list",
    "room_slots",
    "gym_slots",
    "event_list",
    "transit_list",
    "elective_match",
    "action_preview",
    "peer_list",
    "knowledge_answer",
]


@dataclass(frozen=True, slots=True)
class CampusTool:
    name: str
    description: str
    action: ActionName | None
    card_type: CardKind
    is_preview: bool
    extra: Literal["none", "elective", "peers", "knowledge"] = "none"


CAMPUS_TOOLS: tuple[CampusTool, ...] = (
    CampusTool(
        "timetable_today",
        "查询用户今天的课表。无需参数。",
        ActionName.TIMETABLE_TODAY,
        "course_list",
        False,
    ),
    CampusTool(
        "timetable_fetch_term",
        "拉取本学期课表。可选 scan_from/scan_to（周次 1-30）、academic_year（如 2025-2026）、academic_term（1-3）。",
        ActionName.TIMETABLE_FETCH_TERM,
        "course_list",
        False,
    ),
    CampusTool(
        "assignment_list_unfinished",
        "列出未完成作业 / DDL。无需参数。",
        ActionName.ASSIGNMENT_LIST_UNFINISHED,
        "assignment_list",
        False,
    ),
    CampusTool(
        "room_available",
        "查询研讨室空闲。必填 kind（房间类型编号）、date（YYYY-MM-DD）；可选 lab、room。",
        ActionName.ROOM_AVAILABLE,
        "room_slots",
        False,
    ),
    CampusTool(
        "gym_available",
        "查询体育场馆空闲。必填 venue_type（如 羽毛球/健身/游泳/网球/乒乓球/篮球）；可选 date、days(1-7)、venue（如 南校园）、include_full。",
        ActionName.GYM_AVAILABLE,
        "gym_slots",
        False,
    ),
    CampusTool(
        "seminar_list",
        "列出讲座/组会/课题。可选 kind（todayHot/latest/hot/like）、keyword、department、college、tag。",
        ActionName.SEMINAR_LIST,
        "event_list",
        False,
    ),
    CampusTool(
        "career_teachin_list",
        "列出宣讲会。可选 title、event_type、start、end、limit。",
        ActionName.CAREER_TEACHIN_LIST,
        "event_list",
        False,
    ),
    CampusTool(
        "career_jobfair_list",
        "列出招聘会。可选 title、event_type、start、end、limit。",
        ActionName.CAREER_JOBFAIR_LIST,
        "event_list",
        False,
    ),
    CampusTool(
        "transit_bus",
        "查询校内班车。可选 day_type（0工作日/1周末）、from_campus、to_campus、query、upcoming。",
        ActionName.TRANSIT_BUS,
        "transit_list",
        False,
    ),
    CampusTool(
        "transit_qiguan",
        "查询岐关快线。可选 start、to、station、date、available_only。",
        ActionName.TRANSIT_QIGUAN,
        "transit_list",
        False,
    ),
    CampusTool(
        "elective_match_taste",
        "按用户抖音/兴趣画像匹配当前可选公选/选修。可选 question。",
        None,
        "elective_match",
        False,
        "elective",
    ),
    CampusTool(
        "campus_peers",
        "查找已开启社交、可能合得来的同学：同课、同一场馆时段、或兴趣相近。"
        "只返回展示名和重叠理由，不含学号/NetID。用户问「还有谁选了这门课」"
        "「还有谁也约了羽毛球/篮球」或订场后问同一时段还有谁时必须调用。"
        "可选 course_code、venue_type、date、start、question。",
        None,
        "peer_list",
        False,
        "peers",
    ),
    CampusTool(
        "campus_knowledge_search",
        "检索中大校园日常知识库（迎新、宿舍、食堂、校园卡、军训、奖学金、教务常识等）并作答。"
        "课表、订场、找搭子不要用这个工具。参数 question 传用户原话。",
        None,
        "knowledge_answer",
        False,
        "knowledge",
    ),
    CampusTool(
        "room_reserve_preview",
        "生成研讨室预约预览（不会真正下单）。必填 kind、room、date、start、end；可选 lab、members、title、memo、services。",
        ActionName.ROOM_RESERVE_PREVIEW,
        "action_preview",
        True,
    ),
    CampusTool(
        "gym_book_preview",
        "生成体育场馆预约预览（不会真正下单）。必填 venue_type（羽毛球/篮球等）。"
        "今晚打篮球可只传 venue_type=篮球；缺省 date=当天、start=19:00、end=21:00。"
        "可选 venue（校区，如 珠海校区）。用户同时问还有谁约了同一时段时，接着调用 campus_peers。",
        ActionName.GYM_BOOK_PREVIEW,
        "action_preview",
        True,
    ),
    CampusTool(
        "seminar_reserve_preview",
        "生成讲座预约预览（不会真正下单）。必填 seminar_id；可选 source。",
        ActionName.SEMINAR_RESERVE_PREVIEW,
        "action_preview",
        True,
    ),
)

TOOLS_BY_NAME = {tool.name: tool for tool in CAMPUS_TOOLS}


def assert_tool_allowed(name: str) -> CampusTool:
    lowered = name.strip().lower().replace(".", "_").replace("-", "_")
    if any(marker in lowered for marker in FORBIDDEN_TOOL_MARKERS):
        raise AppError("TOOL_FORBIDDEN", "该工具不对 Agent 开放", 403, {"name": name})
    tool = TOOLS_BY_NAME.get(name) or TOOLS_BY_NAME.get(lowered)
    if tool is None:
        raise AppError("TOOL_NOT_ALLOWED", "不在校园白名单内", 403, {"name": name})
    if tool.action is not None:
        definition = CATALOG[tool.action]
        if tool.is_preview:
            if definition.tier != ActionTier.YELLOW or not definition.is_write:
                raise AppError("TOOL_FORBIDDEN", "预览工具配置异常", 500, {"name": name})
        elif definition.is_write or definition.tier != ActionTier.GREEN:
            raise AppError("TOOL_FORBIDDEN", "写操作不对 Agent 开放", 403, {"name": name})
    return tool


def openai_tool_schemas() -> list[dict[str, Any]]:
    """OpenAI-compatible tool definitions for the sidecar LLM loop."""

    schemas: list[dict[str, Any]] = []
    for tool in CAMPUS_TOOLS:
        if tool.extra == "elective":
            parameters: dict[str, Any] = {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户原话，可原样传入",
                    }
                },
                "additionalProperties": False,
            }
        elif tool.extra == "peers":
            parameters = {
                "type": "object",
                "properties": {
                    "course_code": {
                        "type": "string",
                        "description": "课程代码，如 CS2002",
                    },
                    "venue_type": {
                        "type": "string",
                        "description": "运动项目，如 羽毛球/健身/游泳",
                    },
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "start": {"type": "string", "description": "开始时间 HH:mm"},
                    "question": {
                        "type": "string",
                        "description": "用户原话，可原样传入",
                    },
                },
                "additionalProperties": False,
            }
        elif tool.extra == "knowledge":
            parameters = {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户原话，可原样传入",
                    }
                },
                "required": ["question"],
                "additionalProperties": False,
            }
        elif tool.action is None:
            parameters = {"type": "object", "properties": {}, "additionalProperties": False}
        else:
            raw = CATALOG[tool.action].params_type.model_json_schema()
            parameters = {
                "type": "object",
                "properties": raw.get("properties") or {},
                "required": raw.get("required") or [],
                "additionalProperties": False,
            }
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters,
                },
            }
        )
    return schemas


def list_tools_public() -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "card_type": tool.card_type,
            "preview_only": tool.is_preview,
        }
        for tool in CAMPUS_TOOLS
    ]


class _MemorySessionStore:
    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._items: dict[str, tuple[float, dict[str, Any]]] = {}

    def put(self, token: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        with self._guard:
            self._items[token] = (time.time() + ttl_seconds, payload)

    def get(self, token: str) -> dict[str, Any] | None:
        with self._guard:
            item = self._items.get(token)
            if item is None:
                return None
            expires, payload = item
            if expires < time.time():
                self._items.pop(token, None)
                return None
            return dict(payload)


_memory_sessions = _MemorySessionStore()
_redis: Redis | None = None
_redis_disabled_until = 0.0


def _redis_client() -> Redis | None:
    global _redis, _redis_disabled_until
    settings = get_settings()
    if not settings.distributed_locks_enabled or settings.env == "test":
        return None
    if time.monotonic() < _redis_disabled_until:
        return None
    if _redis is None:
        _redis = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.15,
            socket_timeout=0.5,
            decode_responses=True,
        )
    return _redis


def mint_tool_session(
    db: Session,
    user_id: str,
    *,
    question: str = "",
    context: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    grants = list(
        db.scalars(
            select(AuthorizationGrant.scope).where(
                AuthorizationGrant.user_id == user_id,
                AuthorizationGrant.granted.is_(True),
            )
        )
    )
    token = uuid.uuid4().hex
    payload = {
        "user_id": user_id,
        "grants": grants,
        "question": question,
        "context": context or {},
        "issued_at": datetime.now(UTC).isoformat(),
    }
    ttl = max(60, int(settings.tool_session_ttl_seconds))
    client = _redis_client()
    if client is not None:
        try:
            client.setex(f"{SESSION_KEY_PREFIX}{token}", ttl, json.dumps(payload, ensure_ascii=False))
            return token
        except RedisError as exc:
            if settings.is_production:
                raise AppError("SESSION_STORE_UNAVAILABLE", "会话服务暂时不可用", 503) from exc
            global _redis_disabled_until
            _redis_disabled_until = time.monotonic() + 30
    _memory_sessions.put(token, payload, ttl)
    return token


def resolve_tool_session(token: str | None) -> dict[str, Any]:
    if not token or not token.strip():
        raise AppError("TOOL_SESSION_REQUIRED", "缺少 tool_session", 401)
    token = token.strip()
    client = _redis_client()
    raw: str | None = None
    if client is not None:
        try:
            raw = client.get(f"{SESSION_KEY_PREFIX}{token}")
        except RedisError as exc:
            settings = get_settings()
            if settings.is_production:
                raise AppError("SESSION_STORE_UNAVAILABLE", "会话服务暂时不可用", 503) from exc
            global _redis_disabled_until
            _redis_disabled_until = time.monotonic() + 30
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AppError("TOOL_SESSION_INVALID", "tool_session 无效", 401) from exc
        if isinstance(payload, dict) and payload.get("user_id"):
            return payload
        raise AppError("TOOL_SESSION_INVALID", "tool_session 无效", 401)
    payload = _memory_sessions.get(token)
    if not payload or not payload.get("user_id"):
        raise AppError("TOOL_SESSION_INVALID", "tool_session 无效或已过期", 401)
    return payload


def _compact(value: Any, limit: int = 8000) -> Any:
    try:
        encoded = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        encoded = str(value)
    if len(encoded) <= limit:
        return value
    return {"truncated": True, "preview": encoded[:limit], "bytes": len(encoded)}


def _validation_payload(action: ActionName, params: dict[str, Any], exc: ValidationError) -> dict[str, Any]:
    raw_issues = exc.errors(include_url=False)
    required_fields = sorted(
        {
            str(issue["loc"][0])
            for issue in raw_issues
            if issue.get("type") == "missing" and issue.get("loc")
        }
    )
    form_screen = (
        "B6"
        if action.value.startswith("room.")
        else "B5"
        if action.value.startswith("gym.")
        else "B2"
    )
    return {
        "ok": False,
        "kind": "clarification",
        "action": action.value,
        "card_type": "parameter_clarification",
        "message": "需要补齐校园事务参数后才能继续。",
        "required_fields": required_fields,
        "provided_fields": sorted(str(key) for key in params),
        "form_screen": form_screen,
        "issues": [
            {
                "field": ".".join(str(part) for part in issue.get("loc", ())),
                "code": str(issue.get("type", "invalid")),
                "message": str(issue.get("msg", "参数无效")),
            }
            for issue in raw_issues
        ],
    }


def dispatch_tool(
    name: str,
    arguments: dict[str, Any] | None,
    *,
    tool_session: str,
    db: Session | None = None,
) -> dict[str, Any]:
    tool = assert_tool_allowed(name)
    session = resolve_tool_session(tool_session)
    user_id = str(session["user_id"])
    params = dict(arguments or {})
    params.pop("tool_session", None)
    own_db = db is None
    db = db or SessionLocal()
    started = time.perf_counter()
    try:
        if tool.extra == "elective":
            from onemore.modules.campus.elective_hermes import answer_elective_match

            question = str(params.get("question") or session.get("question") or "")
            context = session.get("context") if isinstance(session.get("context"), dict) else {}
            data = answer_elective_match(db, user_id, question, context)
            return {
                "ok": True,
                "kind": "result",
                "action": "elective.match_taste",
                "card_type": tool.card_type,
                "requires_preview": False,
                "data": data,
            }
        if tool.extra == "peers":
            from onemore.modules.campus.peers import suggest_peers

            session_context = session.get("context") if isinstance(session.get("context"), dict) else {}
            context = {**session_context, **params}
            context["question"] = str(params.get("question") or session.get("question") or "")
            if params.get("course_code"):
                context["course_codes"] = [str(params["course_code"])]
            peers = suggest_peers(db, user_id, context)
            return {
                "ok": True,
                "kind": "result",
                "action": "campus.peers",
                "card_type": tool.card_type,
                "requires_preview": False,
                "data": {"peers": peers, "count": len(peers)},
            }
        if tool.extra == "knowledge":
            from onemore.modules.campus.ima_kb import ima_configured, search_campus_knowledge

            question = str(params.get("question") or session.get("question") or "")
            if not ima_configured():
                data = {"message": "校园知识库未配置。", "hits": [], "count": 0}
            else:
                data = search_campus_knowledge(question)
                if not data.get("hits"):
                    data = {
                        **data,
                        "message": "知识库里暂时没找到直接对应的说明，可以换个说法再问。",
                    }
            return {
                "ok": True,
                "kind": "result",
                "action": "campus.knowledge",
                "card_type": tool.card_type,
                "requires_preview": False,
                "data": data,
            }
        assert tool.action is not None
        definition = CATALOG[tool.action]
        if tool.action == ActionName.GYM_BOOK_PREVIEW:
            from onemore.db.models import User
            from onemore.modules.campus.gym_intent import infer_gym_book_params

            question = str(session.get("question") or "")
            params = infer_gym_book_params(question, params)
            user = db.get(User, user_id)
            campus = ((user.campus if user else None) or "").strip()
            if campus and not params.get("venue"):
                params["venue"] = campus
        elif tool.action == ActionName.GYM_AVAILABLE:
            from onemore.db.models import User
            from onemore.modules.campus.gym_intent import infer_gym_available_params

            question = str(session.get("question") or "")
            params = infer_gym_available_params(question, params)
            user = db.get(User, user_id)
            campus = ((user.campus if user else None) or "").strip()
            if campus and not params.get("venue"):
                params["venue"] = campus
        try:
            validated = definition.params_type.model_validate(params)
        except ValidationError as exc:
            return _validation_payload(tool.action, params, exc)
        canonical = validated.model_dump(mode="json")
        if tool.is_preview:
            data: dict[str, Any] = {"params": canonical, "next": "/actions/preview"}
            if tool.action == ActionName.GYM_BOOK_PREVIEW:
                from onemore.modules.campus.gym_intent import gym_preview_message

                data["message"] = gym_preview_message(canonical)
            return {
                "ok": True,
                "kind": "action_preview",
                "action": tool.action.value,
                "card_type": tool.card_type,
                "requires_preview": True,
                "data": data,
            }
        data = action_service.execute_read_action(db, user_id, tool.action, canonical)
        return {
            "ok": True,
            "kind": "result",
            "action": tool.action.value,
            "card_type": tool.card_type,
            "requires_preview": False,
            "data": data,
        }
    except AppError as exc:
        return {
            "ok": False,
            "kind": "error",
            "action": tool.action.value if tool.action else tool.name,
            "card_type": tool.card_type,
            "requires_preview": False,
            "error": {"code": exc.code, "message": exc.message, "details": exc.details or {}},
        }
    finally:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "campus_mcp tool=%s user=%s ms=%s",
            tool.name,
            user_id,
            elapsed_ms,
        )
        if own_db:
            db.close()


def tool_result_for_llm(result: dict[str, Any]) -> str:
    payload = dict(result)
    if "data" in payload:
        payload["data"] = _compact(payload["data"])
    return json.dumps(payload, ensure_ascii=False, default=str)
