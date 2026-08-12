"""Hermes path: Douyin taste persona → JWXT electives match (with competition)."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from pathlib import Path

from onemore.core.config import get_settings
from onemore.core.errors import AppError
from onemore.hermes.executor import executor_pool
from onemore.modules.actions import service as action_service
from onemore.modules.taste_profile import service as taste_service
from onemore.modules.taste_profile.elective_match import match_electives_to_persona

logger = logging.getLogger("onemore.campus.elective_hermes")

ROOT = Path(__file__).resolve().parents[3]
CATALOG_CACHE = ROOT / "artifacts" / "taste" / "elective-catalog-cache.json"

ELECTIVE_QUESTION_HINTS = (
    "公选",
    "选修",
    "选课",
    "通识",
    "学院公选",
    "适合选",
    "推荐课",
    "画像",
    "兴趣匹配",
    "匹配公选",
    "选什么课",
    "什么公选",
)

DEFAULT_CATEGORIES = ("学院公选", "专选", "跨专业选修", "体育选修")
DEFAULT_KEYWORDS = ("人工智能", "大模型", "编程", "创新", "设计", "科技", "创业", "体育")

# Fallback when demo account has no DB taste row yet (matches seed_demo_taste_profile).
DEMO_PERSONA_FALLBACK: dict[str, Any] = {
    "primary_tag": {"key": "explorer_builder", "label": "探索型 Builder", "score": 0.2963},
    "secondary_tags": [
        {"key": "knowledge_curator", "label": "知识策展人", "score": 0.24},
        {"key": "aesthetic_observer", "label": "审美观察者", "score": 0.21},
        {"key": "strategy_player", "label": "策略玩家", "score": 0.18},
    ],
    "interest_domains": [
        {"key": "career_growth", "label": "成长/职业", "score": 0.32},
        {"key": "knowledge_method", "label": "知识方法", "score": 0.27},
        {"key": "ai_programming", "label": "AI/编程", "score": 0.24},
        {"key": "tech_devices", "label": "科技数码", "score": 0.20},
    ],
    "interest_facets": [
        {"label": "黑客松/AI创变"},
        {"label": "华强北硬件"},
        {"label": "运动康复"},
        {"label": "自媒体 IP"},
    ],
    "summary": "一个把兴趣当项目来做的探索者：热衷黑客松与AI实践，也享受跑步康复和旅行取景。",
    "persona": "他是一位自带节奏的实践者。在黑客松里享受极限开发，也把跑步康复和旅行取景当成持续打磨的项目。",
    "matching_hints": ["组队黑客松", "跑步康复", "编程工具", "逛科技市集"],
    "calibrated": False,
}

FAKE_CATALOG: list[dict[str, Any]] = [
    {
        "code": "AHG203",
        "title": "破解学习密码：脑科学+AI跨学科实践",
        "category": "学院公选",
        "credits": 2,
        "campus": "珠海校区",
        "capacity": 48,
        "remaining": 48,
        "selected": 0,
        "selectable": True,
    },
    {
        "code": "SSE369",
        "title": "人工智能与大模型（III）",
        "category": "专业选修",
        "credits": 2,
        "campus": "珠海校区",
        "capacity": 150,
        "remaining": 150,
        "selected": 0,
        "selectable": True,
    },
    {
        "code": "CE1028",
        "title": "AI探索珠江",
        "category": "学院公选",
        "credits": 1,
        "campus": "珠海校区",
        "capacity": 60,
        "remaining": 60,
        "selected": 0,
        "selectable": True,
    },
    {
        "code": "SSE337",
        "title": "3D游戏编程与设计",
        "category": "专业选修",
        "credits": 2,
        "campus": "珠海校区",
        "capacity": 150,
        "remaining": 149,
        "selected": 1,
        "selectable": True,
    },
    {
        "code": "CET921",
        "title": "科幻作品中的未来科技",
        "category": "学院公选",
        "credits": 2,
        "campus": "珠海校区",
        "capacity": 100,
        "remaining": 100,
        "selected": 0,
        "selectable": True,
    },
]


def is_elective_match_question(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return False
    return any(hint in value for hint in ELECTIVE_QUESTION_HINTS)


def _persona_from_profile(db: Session, user_id: str) -> tuple[dict[str, Any], str]:
    profile = taste_service.get_taste_profile(db, user_id)
    if profile is not None:
        sample = profile.sample_summary or {}
        persona = {
            "primary_tag": profile.primary_tag or {},
            "secondary_tags": profile.secondary_tags or [],
            "interest_domains": profile.interest_domains or [],
            "interest_facets": sample.get("interest_facets") or [],
            "summary": profile.summary or "",
            "persona": sample.get("persona") or "",
            "matching_hints": sample.get("matching_hints") or [],
            "calibrated": bool(sample.get("calibrated", False)),
        }
        return persona, "taste_profile"
    if user_id == "u_demo_1":
        return dict(DEMO_PERSONA_FALLBACK), "demo_fallback"
    raise AppError(
        "TASTE_PROFILE_REQUIRED",
        "请先在「我的」导入抖音画像，再问 Hermes 推荐公选",
        409,
        {"next": "/profile/imports/douyin"},
    )


def _extract_items(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [row for row in items if isinstance(row, dict)]
    return []


def _fetch_live_catalog(user_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    courses: list[dict[str, Any]] = []
    seen: set[str] = set()
    meta: dict[str, Any] = {"categories": {}, "keywords": {}, "errors": []}

    def add(items: list[dict[str, Any]]) -> None:
        for item in items:
            key = f"{item.get('code')}|{item.get('title')}"
            if key in seen:
                continue
            seen.add(key)
            courses.append(item)

    for category in DEFAULT_CATEGORIES:
        payload, err = executor_pool.run_cli_json(
            user_id,
            [
                "jwxt",
                "course-selection",
                "list",
                "--category",
                category,
                "--page",
                "1",
                "--size",
                "40",
                "--json",
            ],
            subsystem="jwxt",
            timeout_seconds=90,
        )
        if err:
            meta["errors"].append({"category": category, "error": err})
            meta["categories"][category] = 0
            continue
        items = _extract_items(payload)
        meta["categories"][category] = len(items)
        if isinstance(payload, dict) and payload.get("selectionWindow"):
            meta["selection_window"] = payload.get("selectionWindow")
        add(items)

    # Keyword probes when category lists are sparse.
    if len(courses) < 8:
        for keyword in DEFAULT_KEYWORDS:
            payload, err = executor_pool.run_cli_json(
                user_id,
                [
                    "jwxt",
                    "course-selection",
                    "list",
                    "--keyword",
                    keyword,
                    "--page",
                    "1",
                    "--size",
                    "20",
                    "--json",
                ],
                subsystem="jwxt",
                timeout_seconds=60,
            )
            if err:
                meta["keywords"][keyword] = f"error:{err}"
                continue
            items = _extract_items(payload)
            meta["keywords"][keyword] = len(items)
            add(items)

    return courses, meta


def _load_catalog_cache() -> list[dict[str, Any]]:
    if not CATALOG_CACHE.is_file():
        return []
    try:
        payload = json.loads(CATALOG_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return _extract_items(payload)


def _save_catalog_cache(courses: list[dict[str, Any]]) -> None:
    if not courses:
        return
    try:
        CATALOG_CACHE.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_CACHE.write_text(
            json.dumps(
                {"items": courses, "source": "jwxt_course_selection"},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("failed to write elective catalog cache: %s", exc)


def _compact_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in items:
        compact.append(
            {
                "code": row.get("code"),
                "title": row.get("title"),
                "category": row.get("category"),
                "credits": row.get("credits"),
                "campus": row.get("campus"),
                "college": row.get("college"),
                "weekday": row.get("weekday"),
                "capacity": row.get("capacity"),
                "selected": row.get("selected"),
                "remaining": row.get("remaining"),
                "fill_rate": row.get("fill_rate"),
                "competition_level": row.get("competition_level"),
                "competition_label": row.get("competition_label"),
                "match_score": row.get("match_score"),
                "match_reasons": row.get("match_reasons") or [],
                "selectable": row.get("selectable"),
            }
        )
    return compact


def answer_elective_match(
    db: Session,
    user_id: str,
    text: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Hermes card payload for elective recommendations."""

    context = context or {}
    action_service._check_grant(db, user_id, "curriculum")  # noqa: SLF001 — shared grant gate
    action_service._check_trust(db, user_id, "T1")  # noqa: SLF001

    persona, persona_source = _persona_from_profile(db, user_id)
    # Allow iOS to override / enrich with attached tastePersona.
    attached = context.get("tastePersona") or context.get("taste_persona")
    if isinstance(attached, dict) and attached:
        persona = {**persona, **attached}
        persona_source = "client_context"

    settings = get_settings()
    catalog_meta: dict[str, Any] = {"source": "fake_catalog"}
    if settings.hermes_mode == "fake":
        courses = list(FAKE_CATALOG)
    else:
        attached_catalog = context.get("electiveCatalog") or context.get("elective_catalog")
        if isinstance(attached_catalog, list) and attached_catalog:
            courses = [row for row in attached_catalog if isinstance(row, dict)]
            catalog_meta = {"source": "client_catalog", "count": len(courses)}
        else:
            courses, live_meta = _fetch_live_catalog(user_id)
            catalog_meta = {"source": "jwxt_course_selection", **live_meta}
            login_expired = any(
                err.get("error") == "login_expired"
                for err in (live_meta.get("errors") or [])
                if isinstance(err, dict)
            ) or any(
                str(v).endswith("login_expired")
                for v in (live_meta.get("keywords") or {}).values()
            )
            if courses:
                _save_catalog_cache(courses)
            else:
                cached = _load_catalog_cache()
                if cached:
                    logger.warning(
                        "live elective catalog empty for %s; using cache (%s)",
                        user_id,
                        len(cached),
                    )
                    courses = cached
                    catalog_meta["source"] = "catalog_cache"
                    catalog_meta["note"] = (
                        "教务会话失效或列表暂空，已用本地缓存课表推荐；竞争度可能不是此刻实时值。"
                        if login_expired
                        else "教务列表暂空，已用本地缓存课表推荐。"
                    )
                else:
                    logger.warning(
                        "live elective catalog empty for %s; using fake catalog", user_id
                    )
                    courses = list(FAKE_CATALOG)
                    catalog_meta["source"] = "fake_catalog_fallback"
                    catalog_meta["note"] = "教务列表暂空，已用演示目录回答"
            if login_expired:
                catalog_meta["session_status"] = "login_expired"
                catalog_meta["next"] = "请重新完成企业微信扫码登录以刷新教务会话"

    matched = match_electives_to_persona(persona, courses, limit=10, min_score=1.0)
    primary = persona.get("primary_tag") or {}
    primary_label = (
        primary.get("label") if isinstance(primary, dict) else str(primary or "你的画像")
    )
    items = _compact_items(matched.get("items") or [])
    lines = []
    for index, row in enumerate(items[:6], start=1):
        competition = row.get("competition_label") or "名额未知"
        selected = row.get("selected")
        capacity = row.get("capacity")
        seat = (
            f"已选{selected}/{capacity}"
            if selected is not None and capacity is not None
            else competition
        )
        lines.append(
            f"{index}. {row.get('title')}（{row.get('code')} · {row.get('category')}）"
            f" · {competition} · {seat}"
        )

    message = (
        f"按「{primary_label}」画像，从当前可选课里为你挑了这些（含竞争度）：\n"
        + ("\n".join(lines) if lines else "暂时没有足够匹配的课，可换关键词或稍后再问。")
    )

    return {
        "message": message,
        "question": text,
        "persona_source": persona_source,
        "persona_label": primary_label,
        "catalog": catalog_meta,
        "competition_summary": matched.get("competition_summary") or {},
        "items": items,
        "search_hints": matched.get("search_hints") or [],
        "note": "只读推荐，不会自动选课。正式选课请在教务确认。",
    }
