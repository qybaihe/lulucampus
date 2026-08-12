"""AI enrichment for Douyin taste profiles via OpenCode Go.

Uses OpenCode Go's OpenAI-compatible chat completions endpoint with
**DeepSeek V4 Flash only** (model id: ``deepseek-v4-flash``).

Docs: https://opencode.ai/docs/zh-cn/go
  - Endpoint: https://opencode.ai/zen/go/v1/chat/completions
  - Model:    deepseek-v4-flash

Deterministic tag/domain scores stay in ``analyzer``; this module generates
the human-readable persona summary and interest facets from liked-content
samples. Failures fall back to the rule-based text.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from onemore.core.config import get_settings

logger = logging.getLogger("onemore.taste_profile.llm")

# OpenCode Go · DeepSeek V4 Flash.
# Prefer settings / env; fall back to public defaults for base URL + model only.
# Never commit a real API key — set ONEMORE_TASTE_LLM_API_KEY in .env.
OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"
OPENCODE_GO_MODEL = "deepseek-v4-flash"
OPENCODE_GO_TIMEOUT_SECONDS = 45.0


def _api_key() -> str:
    settings = get_settings()
    return (
        getattr(settings, "taste_llm_api_key", None)
        or getattr(settings, "opencode_go_api_key", None)
        or ""
    ).strip()

MAX_SAMPLE_SNIPPETS = 36
MAX_SNIPPET_CHARS = 110


def llm_enabled() -> bool:
    """LLM is on for real imports; disabled in unit tests / when forced off."""
    settings = get_settings()
    if getattr(settings, "env", "") == "test":
        return False
    if not getattr(settings, "taste_llm_enabled", True):
        return False
    return bool(_api_key())


def _sample_snippets(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    buckets: dict[str, list[dict[str, Any]]] = {"like": [], "collect": [], "post": []}
    for item in items:
        bucket = str(item.get("source_bucket") or "post")
        if bucket not in buckets:
            bucket = "post"
        buckets[bucket].append(item)
    picked = buckets["like"][:16] + buckets["collect"][:16] + buckets["post"][:8]

    snippets: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in picked:
        text = " ".join(
            part
            for part in (
                str(item.get("description") or "").strip(),
                str(item.get("title") or "").strip(),
                " ".join(str(tag) for tag in (item.get("hashtags") or [])[:5]),
            )
            if part
        )
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 8:
            continue
        key = text[:48]
        if key in seen:
            continue
        seen.add(key)
        source = str(item.get("source_bucket") or "post")
        if source not in {"like", "collect"}:
            source = "post"
        snippets.append({"source": source, "text": text[:MAX_SNIPPET_CHARS]})
        if len(snippets) >= MAX_SAMPLE_SNIPPETS:
            break
    return snippets


def enrich_provisional_profile(
    result: dict[str, Any],
    items: list[dict[str, Any]] | None = None,
    *,
    quiz_answers: list[dict[str, Any]] | None = None,
    quiz_questions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate persona summary / interest_facets via DeepSeek V4 Flash.

    Never invents new primary_tag keys; only rewrites narrative fields.
    When ``quiz_answers`` is provided (iOS refinement quiz), the model is told
    to tighten the narrative around the user's explicit choices.
    """
    if not llm_enabled() or not items:
        result.setdefault("sample", {})
        result["sample"]["generation"] = "rule"
        return result

    snippets = _sample_snippets(items)
    if not snippets:
        result.setdefault("sample", {})
        result["sample"]["generation"] = "rule"
        return result

    allowed_tags = {
        (result.get("primary_tag") or {}).get("key"),
        *{(tag or {}).get("key") for tag in (result.get("secondary_tags") or [])},
    }
    allowed_tags.discard(None)
    domain_keys = [item.get("key") for item in (result.get("interest_domains") or []) if item.get("key")]

    # Map question_id → prompt / option labels so the model sees human text, not ids only.
    question_index: dict[str, dict[str, Any]] = {}
    for question in quiz_questions or []:
        if isinstance(question, dict) and question.get("id"):
            question_index[str(question["id"])] = question

    quiz_payload: list[dict[str, Any]] = []
    for answer in quiz_answers or []:
        if not isinstance(answer, dict):
            continue
        qid = str(answer.get("question_id") or "")
        oid = str(answer.get("option_id") or "")
        question = question_index.get(qid) or {}
        options = {
            str(opt.get("id")): str(opt.get("label") or opt.get("id"))
            for opt in (question.get("options") or [])
            if isinstance(opt, dict)
        }
        quiz_payload.append(
            {
                "question_id": qid,
                "prompt": question.get("prompt") or qid,
                "option_id": oid,
                "option_label": options.get(oid, oid),
            }
        )

    # Prefer rule-scored quiz facets so LLM does not drop user choices.
    quiz_facets = [
        facet
        for facet in (result.get("interest_facets") or [])
        if isinstance(facet, dict) and facet.get("source") == "quiz"
    ]

    payload = {
        "primary_tag": result.get("primary_tag"),
        "secondary_tags": result.get("secondary_tags"),
        "interest_domains": result.get("interest_domains"),
        "dimensions": result.get("dimensions"),
        "rule_summary": result.get("summary"),
        "quiz_facets": quiz_facets,
        "quiz_answers": quiz_payload,
        "calibrated": bool(result.get("calibrated")),
        "allowed_tag_keys": sorted(str(k) for k in allowed_tags if k),
        "allowed_domain_keys": domain_keys,
        "content_snippets": snippets,
        "sample_size": (result.get("sample") or {}).get("items") or len(items),
    }
    if quiz_payload:
        system = (
            "你是校园成局产品「噜噜成局」的抖音兴趣画像分析师。"
            "用户已完成内容采集，并在 App 内回答了 3–5 道兴趣细化题。"
            "请结合：① 抖音喜欢与收藏样本 ② 结构化分数 ③ 用户答题选择，"
            "生成更精准、更具体的中文人物画像。"
            "要求：\n"
            "1) 必须体现 quiz_answers 里的具体选择，不要忽略用户回答；\n"
            "2) 不要说教，不要空话，不要提抖音/算法/模型/OpenCode；\n"
            "3) 不要改动 primary_tag.key / secondary_tags 的 key；\n"
            "4) interest_facets 的 domain 必须在 allowed_domain_keys 内；"
            "可保留 quiz_facets 并补充 1–3 个更细的点；\n"
            "5) 只输出 JSON，字段：\n"
            "   - summary: string，60-120 字，一句话画像（要更具体）\n"
            "   - persona: string，80-180 字，气质与行动风格\n"
            "   - interest_facets: array of {domain, facet, label}，2-5 个\n"
            "   - matching_hints: array of string，2-4 条成局/匹配短提示\n"
            "   - tone: string\n"
        )
    else:
        system = (
            "你现在不是分析师，你是「噜噜成局」里的水豚噜噜：圆、慢半拍、刚看完对方的内容，抬起头跟「你」说话。\n"
            "样本来自最近的喜欢、收藏和作品；收藏是更有意存下来的，和喜欢一起看。\n"
            "要求：\n"
            "1) persona 必须第一人称（我）对第二人称（你）；像口头短句，不要书面鉴定腔；\n"
            "2) 先点出 content_snippets 里 1-2 件具体事，再轻轻落到这个人怎么成局；\n"
            "3) 允许一点点水豚身体感：慢慢看完、嗯了一下、拍拍、把局凑上。不要堆叠萌词；\n"
            "4) 禁止：这位用户、该账号、作为一名、画像、标签、算法、模型、抖音、喜欢列表、说教、鸡汤、列点；\n"
            "5) 不要改动 primary_tag.key；interest_facets 的 domain 必须在 allowed_domain_keys 内；\n"
            "6) 只输出 JSON，字段：\n"
            "   - summary: string，40-90 字，给卡片看的一句人味描述，仍用「你」\n"
            "   - persona: string，70-140 字，噜噜刚看完抬头发的评语\n"
            "   - interest_facets: array of {domain, facet, label}，2-5 个\n"
            "   - matching_hints: array of string，2-4 条噜噜口吻短句，每条不超过 28 字\n"
            "   - tone: string\n"
        )
    user = json.dumps(payload, ensure_ascii=False)
    try:
        data = _chat_json(system=system, user=user)
    except Exception as exc:  # noqa: BLE001 — enrichment is best-effort
        logger.warning(
            "taste llm enrichment skipped: %s: %s",
            type(exc).__name__,
            str(exc)[:240],
        )
        result.setdefault("sample", {})
        result["sample"]["generation"] = "rule"
        result["sample"]["llm_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
        return result

    summary = data.get("summary")
    if isinstance(summary, str) and 12 <= len(summary.strip()) <= 200:
        result["summary"] = summary.strip()

    sample = result.setdefault("sample", {})
    persona = data.get("persona")
    if isinstance(persona, str) and 12 <= len(persona.strip()) <= 320:
        sample["persona"] = persona.strip()[:280]

    hints = data.get("matching_hints")
    if isinstance(hints, list):
        cleaned_hints = [
            str(item).strip()[:36]
            for item in hints
            if isinstance(item, (str, int, float)) and str(item).strip()
        ][:4]
        if cleaned_hints:
            sample["matching_hints"] = cleaned_hints

    facets_in = data.get("interest_facets") or data.get("interest_domains")
    domain_key_set = set(domain_keys)
    facets: list[dict[str, Any]] = []
    # Keep quiz-sourced facets first so user answers stay visible.
    for entry in quiz_facets:
        domain = str(entry.get("domain") or "")
        facet = str(entry.get("facet") or "")
        label = str(entry.get("label") or facet)
        if domain and facet:
            facets.append(
                {
                    "domain": domain,
                    "facet": facet[:48],
                    "label": label[:48],
                    "source": "quiz",
                    "question_id": entry.get("question_id"),
                }
            )
    if isinstance(facets_in, list):
        for entry in facets_in:
            if not isinstance(entry, dict):
                continue
            domain = str(entry.get("domain") or entry.get("domain_key") or "")
            facet = str(entry.get("facet") or entry.get("key") or "")
            label = str(entry.get("label") or entry.get("facet_label") or facet)
            if domain not in domain_key_set or not facet:
                continue
            if any(item.get("facet") == facet and item.get("domain") == domain for item in facets):
                continue
            facets.append(
                {
                    "domain": domain,
                    "facet": facet[:48],
                    "label": label[:48],
                    "source": "llm",
                }
            )
            if len(facets) >= 6:
                break
    if facets:
        result["interest_facets"] = facets
        sample["interest_facets"] = facets

    sample["generation"] = "llm"
    sample["llm_provider"] = "opencode-go"
    sample["llm_model"] = OPENCODE_GO_MODEL
    if quiz_payload:
        sample["refined_with_quiz"] = True
    if isinstance(data.get("tone"), str):
        sample["tone"] = data["tone"][:40]
    # Bubble narrative fields to top-level for unified TasteProfileResultView.
    if sample.get("persona"):
        result["persona"] = sample["persona"]
    if sample.get("matching_hints"):
        result["matching_hints"] = sample["matching_hints"]
    return result


def _chat_json(*, system: str, user: str) -> dict[str, Any]:
    """Call OpenCode Go chat/completions with DeepSeek V4 Flash only."""
    settings = get_settings()
    base_url = (
        getattr(settings, "taste_llm_base_url", None) or OPENCODE_GO_BASE_URL
    ).rstrip("/")
    # Force DeepSeek V4 Flash — other models are intentionally not selectable here.
    model = getattr(settings, "taste_llm_model", None) or OPENCODE_GO_MODEL
    api_key = _api_key()
    if not api_key:
        raise RuntimeError("ONEMORE_TASTE_LLM_API_KEY is not configured")
    timeout = float(
        getattr(settings, "taste_llm_timeout_seconds", None) or OPENCODE_GO_TIMEOUT_SECONDS
    )

    body = {
        "model": model,
        "temperature": 0.35,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # OpenAI-compatible; DeepSeek on OpenCode Go accepts this.
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Cloudflare on opencode.ai rejects bare python clients (error 1010).
        "User-Agent": "ONE-MORE/1.0 (+https://github.com/onemore; taste-llm)",
        "Accept": "application/json",
    }
    url = f"{base_url}/chat/completions"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            # Surface RegionError / credits messages for operators.
            detail = response.text[:400]
            raise RuntimeError(f"opencode go http {response.status_code}: {detail}")
        payload = response.json()

    message = ((payload.get("choices") or [{}])[0]).get("message") or {}
    content = message.get("content") or ""
    if not content:
        # Some reasoning models put text only in reasoning_content — reject.
        raise RuntimeError("empty llm content")

    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise RuntimeError("llm json is not an object")
    return data
