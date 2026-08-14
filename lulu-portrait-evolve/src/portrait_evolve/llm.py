"""Optional narrative renderer. Never writes scores.

Default channel matches the main-site Douyin enricher: OpenAI-compatible
Chat Completions, model id ``deepseek-v4-flash``. Disabled unless
``PORTRAIT_LLM_API_KEY`` is set. Any failure falls back to templates.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from portrait_evolve.narrative import render
from portrait_evolve.portrait import Portrait

DEFAULT_BASE_URL = "https://opencode.ai/zen/go/v1"
DEFAULT_MODEL = "deepseek-v4-flash"


def configured() -> bool:
    return bool(os.environ.get("PORTRAIT_LLM_API_KEY", "").strip())


def enrich(portrait: Portrait, template: dict[str, Any] | None = None) -> dict[str, Any]:
    base = template or render(portrait)
    if not configured():
        return base
    try:
        rewritten = _complete(portrait, base)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return base
    persona = str(rewritten.get("persona") or "").strip()
    ice = [str(item).strip() for item in (rewritten.get("icebreakers") or []) if str(item).strip()]
    if not persona:
        return base
    return {
        **base,
        "persona": persona,
        "icebreakers": ice[:3] or base["icebreakers"],
        "source": "llm",
        "model": os.environ.get("PORTRAIT_LLM_MODEL", DEFAULT_MODEL),
    }


def _complete(portrait: Portrait, template: dict[str, Any]) -> dict[str, Any]:
    key = os.environ["PORTRAIT_LLM_API_KEY"].strip()
    base_url = os.environ.get("PORTRAIT_LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("PORTRAIT_LLM_MODEL", DEFAULT_MODEL)
    payload = {
        "model": model,
        "temperature": 0.4,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你只改写校园画像的人格短文和破冰句。禁止输出分数、标签 key、置信度。"
                    "不要出现「该用户」「作为一名」「算法」。用中文，像认识这个人的学长。"
                    "只返回 JSON：{\"persona\": \"...\", \"icebreakers\": [\"...\", \"...\"]}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "primary": portrait.primary_tag.to_dict() if portrait.primary_tag else None,
                        "summary": portrait.summary,
                        "template": template,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no json")
    return json.loads(content[start : end + 1])
