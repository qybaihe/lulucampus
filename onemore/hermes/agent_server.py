"""Thin Hermes Agent sidecar: OpenAI-compatible loop over Campus MCP only.

This process must not mount vaults or invoke sysu-anything. It talks to
OpenCode Go for the LLM and to OneMore Campus MCP for tools.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from onemore.core.config import get_settings
from onemore.hermes.campus_mcp import CAMPUS_TOOLS, openai_tool_schemas, tool_result_for_llm

logger = logging.getLogger("onemore.hermes.agent_server")

SYSTEM_PROMPT = """你是中大校园事务 Agent「Lulu Hermes」。
你只能使用提供的校园白名单工具，禁止编造课表/场地/公选结果。
规则：
1. 只处理课表、作业 DDL、研讨室、体育场馆、讲座、宣讲会/招聘会、班车/岐关、按画像推荐公选。
2. 写操作只能调用 *_preview 工具，生成预览后请用户在 App 里确认；绝不可声称已经预约成功。
3. 没有对应工具时，用一两句中文说明你能做什么，并给 1-2 个例子。
4. 工具参数不够时先追问缺的字段，或调用 preview 让服务端返回补参说明。
5. 回复尽量短：有工具结果时只写一两句导语。课程/课表细节不要在正文里再列一遍，App 会用卡片展示。
6. 不要写「不会自动选课」「只读推荐」「正式选课请在教务确认」这类说明。
7. 需要分段时请换行；不要把整段挤成一行。不要提 shell、浏览器、CLI、模型名称。
8. 公选推荐用 elective_match_taste；今天课表用 timetable_today。
9. 南校园羽毛球等场馆查询：gym_available，venue_type 用运动项目（如羽毛球），venue 用校区（如南校园）。
"""


class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    tool_session: str = Field(min_length=8, max_length=128)
    max_tool_rounds: int | None = None
    stream: bool = False


def _settings_llm() -> tuple[str, str, str, float]:
    settings = get_settings()
    base = (settings.hermes_agent_base_url or settings.taste_llm_base_url or "").rstrip("/")
    model = settings.hermes_agent_model or settings.taste_llm_model or "deepseek-v4-flash"
    key = (settings.hermes_agent_api_key or settings.taste_llm_api_key or "").strip()
    timeout = float(settings.hermes_agent_llm_timeout_seconds)
    return base, model, key, timeout


def _mcp_headers() -> dict[str, str]:
    settings = get_settings()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = (settings.campus_mcp_token or "").strip()
    if token:
        headers["X-Campus-MCP-Token"] = token
    return headers


def _call_mcp(name: str, arguments: dict[str, Any], tool_session: str) -> dict[str, Any]:
    settings = get_settings()
    url = settings.campus_mcp_url.rstrip("/") + "/tools/call"
    with httpx.Client(timeout=httpx.Timeout(connect=2.0, read=55.0, write=10.0, pool=2.0)) as client:
        response = client.post(
            url,
            headers=_mcp_headers(),
            json={"name": name, "arguments": arguments, "tool_session": tool_session},
        )
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, dict):
        return {"ok": False, "kind": "error", "error": {"message": "MCP 返回异常"}}
    return data


def _llm_chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
    base, model, key, timeout = _settings_llm()
    if not base or not key:
        raise RuntimeError("Hermes Agent LLM 未配置")
    body: dict[str, Any] = {
        "model": model,
        "temperature": 0.2,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "ONE-MORE/1.0 (+https://github.com/onemore; hermes-agent)",
        "Accept": "application/json",
    }
    url = f"{base}/chat/completions"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            # Some providers reject the tools field; retry without it only if 400.
            if response.status_code == 400 and "tool" in response.text.lower():
                body.pop("tools", None)
                body.pop("tool_choice", None)
                response = client.post(url, headers=headers, json=body)
            if response.status_code >= 400:
                raise RuntimeError(f"opencode go http {response.status_code}: {response.text[:400]}")
        return response.json()


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


_SYNTHETIC_CALL = re.compile(
    r'\{\s*"(?:tool|name)"\s*:\s*"(?P<name>[a-z0-9_]+)"\s*,\s*"(?:arguments|args)"\s*:\s*(?P<args>\{.*?\})\s*\}',
    re.DOTALL,
)


def _synthetic_tool_calls(content: str) -> list[dict[str, Any]]:
    allowed = {tool.name for tool in CAMPUS_TOOLS}
    calls: list[dict[str, Any]] = []
    for match in _SYNTHETIC_CALL.finditer(content or ""):
        name = match.group("name")
        if name not in allowed:
            continue
        arguments = _parse_arguments(match.group("args"))
        calls.append(
            {
                "id": f"synth-{name}-{len(calls)}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
            }
        )
    return calls


def _trace_item(name: str, result: dict[str, Any]) -> dict[str, Any]:
    ok = bool(result.get("ok"))
    summary = "已完成" if ok else "失败"
    if result.get("kind") == "clarification":
        summary = "需要补参"
    elif result.get("kind") == "action_preview":
        summary = "已生成预览"
    error = result.get("error")
    if isinstance(error, dict) and error.get("message"):
        summary = str(error["message"])[:80]
    return {"name": name, "ok": ok, "summary": summary, "card_type": result.get("card_type")}


def run_agent_loop(user_text: str, tool_session: str, max_rounds: int) -> dict[str, Any]:
    tools = openai_tool_schemas()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    trace: list[dict[str, Any]] = []
    last_structured: dict[str, Any] | None = None
    deadline = time.monotonic() + float(get_settings().hermes_agent_timeout_seconds)
    allowed = {tool.name for tool in CAMPUS_TOOLS}

    for _ in range(max(1, max_rounds)):
        if time.monotonic() > deadline:
            break
        payload = _llm_chat(messages, tools)
        message = ((payload.get("choices") or [{}])[0]).get("message") or {}
        assistant = {
            "role": "assistant",
            "content": message.get("content") or "",
        }
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            tool_calls = _synthetic_tool_calls(message.get("content") or "")
        if tool_calls:
            assistant["tool_calls"] = tool_calls
        messages.append(assistant)
        if not tool_calls:
            return {
                "message": (message.get("content") or "").strip(),
                "tool_trace": trace,
                "structured": last_structured,
            }
        for call in tool_calls:
            function = call.get("function") or {}
            name = str(function.get("name") or "")
            arguments = _parse_arguments(function.get("arguments"))
            if name not in allowed:
                result = {
                    "ok": False,
                    "kind": "error",
                    "error": {"code": "TOOL_NOT_ALLOWED", "message": f"{name} 不在校园白名单"},
                }
            else:
                try:
                    result = _call_mcp(name, arguments, tool_session)
                except Exception as exc:  # noqa: BLE001 — tool errors belong in the loop
                    logger.warning("mcp call failed name=%s err=%s", name, exc)
                    result = {
                        "ok": False,
                        "kind": "error",
                        "error": {"code": "MCP_CALL_FAILED", "message": str(exc)[:200]},
                    }
            trace.append(_trace_item(name, result))
            if result.get("ok") or result.get("kind") in {"clarification", "action_preview"}:
                last_structured = result
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id") or name,
                    "name": name,
                    "content": tool_result_for_llm(result),
                }
            )

    # One last text turn without tools if we hit the round cap with pending results.
    if last_structured and time.monotonic() <= deadline:
        try:
            payload = _llm_chat(messages, [])
            message = ((payload.get("choices") or [{}])[0]).get("message") or {}
            text = (message.get("content") or "").strip()
        except Exception:  # noqa: BLE001
            text = ""
    else:
        text = ""
    if not text:
        text = "已经查过校园工具，结果见下方卡片。" if last_structured else "这一轮没有完成校园查询，请稍后再试。"
    return {"message": text, "tool_trace": trace, "structured": last_structured}


app = FastAPI(title="onemore-hermes-agent", docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "hermes-agent"}


@app.post("/v1/chat/completions")
def chat_completions(body: ChatRequest) -> dict[str, Any]:
    settings = get_settings()
    user_text = ""
    for item in reversed(body.messages):
        if item.role == "user" and item.content:
            user_text = item.content.strip()
            break
    if not user_text:
        user_text = "（空问题）"
    max_rounds = body.max_tool_rounds or settings.hermes_agent_max_tool_rounds
    result = run_agent_loop(user_text, body.tool_session, int(max_rounds))
    content = result["message"]
    return {
        "id": "hermes-agent",
        "object": "chat.completion",
        "model": settings.hermes_agent_model or settings.taste_llm_model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "tool_trace": result["tool_trace"],
        "structured": result["structured"],
    }
