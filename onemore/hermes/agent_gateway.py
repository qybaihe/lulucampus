"""Call the Hermes Agent sidecar and map the reply onto HermesAskResult."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.hermes.campus_mcp import mint_tool_session

logger = logging.getLogger("onemore.hermes.agent_gateway")


def agent_sidecar_enabled() -> bool:
    settings = get_settings()
    if settings.env == "test":
        return False
    return settings.hermes_agent_mode == "sidecar"


def map_sidecar_payload(payload: dict[str, Any], fallback_text: str) -> dict[str, Any]:
    message = ""
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if isinstance(choices, list) and choices:
        message = str(((choices[0] or {}).get("message") or {}).get("content") or "").strip()
    if not message:
        message = str(payload.get("message") or fallback_text).strip()
    trace = payload.get("tool_trace") if isinstance(payload.get("tool_trace"), list) else []
    structured = payload.get("structured") if isinstance(payload.get("structured"), dict) else None

    if structured:
        kind = str(structured.get("kind") or "agent")
        action = structured.get("action")
        card_type = str(structured.get("card_type") or "agent_reply")
        requires_preview = bool(structured.get("requires_preview"))
        data = structured.get("data")
        if not isinstance(data, dict):
            data = {"value": data} if data is not None else {}
        if kind == "clarification":
            data = {
                "message": structured.get("message") or message or "需要补齐校园事务参数后才能继续。",
                "required_fields": structured.get("required_fields") or [],
                "provided_fields": structured.get("provided_fields") or [],
                "form_screen": structured.get("form_screen") or "B2",
                "issues": structured.get("issues") or [],
                "tool_trace": trace,
            }
            return {
                "kind": "clarification",
                "action": action,
                "card_type": "parameter_clarification",
                "data": data,
                "requires_preview": False,
                "tool_trace": trace,
            }
        data = {**data, "message": message or data.get("message") or "", "tool_trace": trace}
        if kind not in {"action_preview", "result", "help", "clarification"}:
            kind = "agent"
        if requires_preview:
            kind = "action_preview"
        elif kind == "result":
            kind = "agent"
        return {
            "kind": kind,
            "action": action,
            "card_type": card_type,
            "data": data,
            "requires_preview": requires_preview,
            "tool_trace": trace,
        }

    return {
        "kind": "agent",
        "action": None,
        "card_type": "agent_reply",
        "data": {"message": message or "我主要处理课表、DDL、场地、活动、班车，以及按画像推荐公选。", "tool_trace": trace},
        "requires_preview": False,
        "tool_trace": trace,
    }


def ask_via_sidecar(db: Session, user_id: str, text: str, context: dict[str, Any]) -> dict[str, Any] | None:
    if not agent_sidecar_enabled():
        return None
    settings = get_settings()
    url = (settings.hermes_agent_url or "").rstrip("/")
    if not url:
        return None
    try:
        session = mint_tool_session(db, user_id, question=text, context=context)
    except Exception as exc:  # noqa: BLE001
        logger.warning("mint tool_session failed: %s", exc)
        return None

    timeout = httpx.Timeout(
        connect=min(2.0, settings.hermes_agent_timeout_seconds),
        read=settings.hermes_agent_timeout_seconds,
        write=10.0,
        pool=2.0,
    )
    body = {
        "model": settings.hermes_agent_model or settings.taste_llm_model,
        "messages": [{"role": "user", "content": text}],
        "tool_session": session,
        "max_tool_rounds": settings.hermes_agent_max_tool_rounds,
        "stream": False,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(f"{url}/v1/chat/completions", json=body)
            if response.status_code >= 400:
                logger.warning("hermes sidecar http %s: %s", response.status_code, response.text[:240])
                return None
            payload = response.json()
    except Exception as exc:  # noqa: BLE001 — sidecar down → rule fallback
        logger.warning("hermes sidecar unavailable: %s", exc)
        return None
    if not isinstance(payload, dict):
        return None
    return map_sidecar_payload(payload, text)
