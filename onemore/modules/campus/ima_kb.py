"""Tencent IMA campus knowledge for Hermes.

Credentials stay in Settings / .env. Responses never include API keys,
signed download URLs, or request headers.
"""

from __future__ import annotations

import io
import logging
import math
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import httpx

from onemore.core.config import get_settings

logger = logging.getLogger("onemore.campus.ima_kb")

IMA_WIKI_PREFIX = "/openapi/wiki/v1"
PREFERRED_KB_NAMES = ("迎新Agent", "迎新")
STOP_PHRASES = (
    "需要注意什么",
    "要注意什么",
    "需要注意",
    "注意什么",
    "怎么办",
    "怎么走",
    "怎么去",
    "怎么",
    "什么是",
    "什么",
    "如何",
    "哪些",
    "有没有",
    "可以吗",
    "在哪里",
    "在哪儿",
    "哪里",
    "哪儿",
    "吗",
    "呢",
    "啊",
)
ALIASES = {
    "校园卡": "逸仙卡",
    "逸仙卡": "校园卡",
    "一卡通": "校园卡",
    "虚拟卡": "校园卡",
}
SKIP_QUESTIONS = {"你好", "在吗", "hello", "hi", "hey", "谢谢", "thanks"}
_DOCX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_CACHE_TTL_SECONDS = 1800.0
_MAX_ANSWER_CHARS = 900
_MAX_HITS = 3

_cache: dict[str, tuple[float, Any]] = {}


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    title: str
    question: str
    text: str
    source: str
    media_id: str


def ima_configured() -> bool:
    settings = get_settings()
    return bool(settings.ima_openapi_client_id.strip() and settings.ima_openapi_api_key.strip())


def answer_campus_knowledge(question: str) -> dict[str, Any] | None:
    if not ima_configured():
        return None
    body = (question or "").strip()
    if len(body) < 2 or body.lower() in SKIP_QUESTIONS:
        return None
    try:
        payload = search_campus_knowledge(body)
    except Exception as exc:  # noqa: BLE001 — rules fallback should stay quiet
        logger.warning("ima knowledge search failed: %s", type(exc).__name__)
        return None
    hits = payload.get("hits") or []
    message = str(payload.get("message") or "").strip()
    if not hits or not message:
        return None
    return {
        "kind": "result",
        "action": "campus.knowledge",
        "card_type": "knowledge_answer",
        "data": {
            "message": message,
            "hits": hits,
            "count": len(hits),
            "source": "ima",
        },
        "requires_preview": False,
    }


def search_campus_knowledge(question: str) -> dict[str, Any]:
    chunks = list(_load_chunks())
    chunks.extend(_chunks_from_title_matches(question))
    ranked = _rank_chunks(question, chunks)
    if not ranked:
        return {"hits": [], "message": "", "count": 0}
    top = ranked[:_MAX_HITS]
    primary = top[0]
    message = _format_answer(primary.question, primary.text)
    hits = [
        {
            "title": item.question or item.title,
            "source": item.source,
            "snippet": _snippet(item.text, 160),
        }
        for item in top
    ]
    return {"hits": hits, "message": message, "count": len(hits)}


def _settings_tuple() -> tuple[str, str, str, str, float]:
    settings = get_settings()
    return (
        settings.ima_openapi_base_url.rstrip("/"),
        settings.ima_openapi_client_id.strip(),
        settings.ima_openapi_api_key.strip(),
        settings.ima_knowledge_base_id.strip(),
        float(settings.ima_kb_timeout_seconds),
    )


def _cache_get(key: str) -> Any | None:
    item = _cache.get(key)
    if item is None:
        return None
    expires, value = item
    if expires < time.monotonic():
        _cache.pop(key, None)
        return None
    return value


def _cache_put(key: str, value: Any, ttl: float = _CACHE_TTL_SECONDS) -> Any:
    _cache[key] = (time.monotonic() + ttl, value)
    return value


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    base, client_id, api_key, _, timeout = _settings_tuple()
    url = f"{base}{path if path.startswith('/') else '/' + path}"
    headers = {
        "Content-Type": "application/json",
        "ima-openapi-clientid": client_id,
        "ima-openapi-apikey": api_key,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=body)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("ima response invalid")
    code = payload.get("code", payload.get("retcode"))
    if code not in (0, None):
        raise RuntimeError(str(payload.get("msg") or payload.get("errmsg") or "ima error"))
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _download_bytes(url: str, headers: dict[str, str] | None) -> bytes:
    _, _, _, _, timeout = _settings_tuple()
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url, headers=headers or {})
        response.raise_for_status()
        return response.content


def resolve_knowledge_base_id() -> str:
    cached = _cache_get("kb_id")
    if isinstance(cached, str) and cached:
        return cached
    _, _, _, configured, _ = _settings_tuple()
    if configured:
        return _cache_put("kb_id", configured)
    data = _post(
        f"{IMA_WIKI_PREFIX}/get_addable_knowledge_base_list",
        {"cursor": "", "limit": 20},
    )
    bases = data.get("addable_knowledge_base_list") or []
    picked = ""
    for item in bases:
        name = str(item.get("name") or "")
        if any(marker in name for marker in PREFERRED_KB_NAMES):
            picked = str(item.get("id") or "")
            break
    if not picked and bases:
        picked = str(bases[0].get("id") or "")
    if not picked:
        raise RuntimeError("ima knowledge base missing")
    return _cache_put("kb_id", picked)


def _list_files() -> list[dict[str, Any]]:
    cached = _cache_get("files")
    if isinstance(cached, list):
        return cached
    kb_id = resolve_knowledge_base_id()
    data = _post(
        f"{IMA_WIKI_PREFIX}/get_knowledge_list",
        {"cursor": "", "limit": 50, "knowledge_base_id": kb_id},
    )
    files = [item for item in (data.get("knowledge_list") or []) if isinstance(item, dict)]
    return _cache_put("files", files)


def _media_text(media_id: str, title: str) -> str:
    key = f"media:{media_id}"
    cached = _cache_get(key)
    if isinstance(cached, str):
        return cached
    info = _post(f"{IMA_WIKI_PREFIX}/get_media_info", {"media_id": media_id})
    url_info = info.get("url_info") if isinstance(info.get("url_info"), dict) else {}
    url = str(url_info.get("url") or "").strip()
    if not url:
        return _cache_put(key, "")
    headers = {
        str(name): str(value)
        for name, value in (url_info.get("headers") or {}).items()
        if name and value is not None
    }
    raw = _download_bytes(url, headers)
    text = _extract_text(title, raw)
    return _cache_put(key, text)


def _extract_text(title: str, raw: bytes) -> str:
    lowered = title.lower()
    if lowered.endswith(".md") or raw[:1] in (b"#", b">") or b"**Q" in raw[:200]:
        return raw.decode("utf-8", errors="replace")
    if lowered.endswith(".docx") or raw[:2] == b"PK":
        try:
            return _docx_text(raw)
        except Exception:  # noqa: BLE001
            logger.warning("ima docx extract failed title_len=%s", len(title))
            return ""
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _docx_text(raw: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{_DOCX_NS}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_DOCX_NS}t")).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _parse_qa_markdown(source: str, media_id: str, markdown: str) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    parts = re.split(r"\n(?=\*\*Q\d+：)", markdown)
    for part in parts:
        match = re.match(r"\*\*Q\d+：(.+?)\*\*\s*(.*)", part, re.S)
        if not match:
            continue
        question = match.group(1).strip()
        answer = re.sub(r"\n\*—\s*.*$", "", match.group(2).strip(), flags=re.M).strip()
        answer = re.sub(r"\n{3,}", "\n\n", answer)
        if question and answer:
            chunks.append(
                KnowledgeChunk(
                    title=question,
                    question=question,
                    text=answer,
                    source=source,
                    media_id=media_id,
                )
            )
    return chunks


def _parse_numbered_doc(source: str, media_id: str, text: str) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    parts = re.split(r"\n(?=\d+[\.、])", text.strip())
    for part in parts:
        match = re.match(r"\d+[\.、]\s*(.+?)(?:\n+|$)(.*)", part, re.S)
        if not match:
            continue
        question = match.group(1).strip()
        body = match.group(2).strip() or part.strip()
        if len(question) < 4:
            continue
        chunks.append(
            KnowledgeChunk(
                title=question,
                question=question,
                text=body or question,
                source=source,
                media_id=media_id,
            )
        )
    if not chunks and text.strip():
        chunks.append(
            KnowledgeChunk(
                title=source,
                question=source,
                text=text.strip(),
                source=source,
                media_id=media_id,
            )
        )
    return chunks


def _load_chunks() -> list[KnowledgeChunk]:
    cached = _cache_get("qa_chunks")
    if isinstance(cached, list):
        return cached
    chunks: list[KnowledgeChunk] = []
    for item in _list_files():
        title = str(item.get("title") or "")
        media_id = str(item.get("media_id") or "")
        if not media_id:
            continue
        if "QA" not in title and not title.lower().endswith(".md"):
            continue
        markdown = _media_text(media_id, title)
        chunks.extend(_parse_qa_markdown(title, media_id, markdown))
    return _cache_put("qa_chunks", chunks)


def _chunks_from_title_matches(question: str) -> list[KnowledgeChunk]:
    query = _content_query(question)
    files = _list_files()
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in files:
        title = str(item.get("title") or "")
        if "QA" in title:
            continue
        score = _overlap_score(query, title)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    chunks: list[KnowledgeChunk] = []
    for _, item in scored[:2]:
        title = str(item.get("title") or "")
        media_id = str(item.get("media_id") or "")
        text = _media_text(media_id, title)
        if title.lower().endswith(".md"):
            chunks.extend(_parse_qa_markdown(title, media_id, text))
        else:
            chunks.extend(_parse_numbered_doc(title, media_id, text))
    return chunks


def _content_query(question: str) -> str:
    text = re.sub(r"\s+", "", question or "")
    for phrase in STOP_PHRASES:
        text = text.replace(phrase, " ")
    text = re.sub(r"[？?。！!，,、]", " ", text)
    expanded = [text]
    for src, dst in ALIASES.items():
        if src in text and dst not in text:
            expanded.append(text.replace(src, dst))
    return " ".join(expanded)


def _grams(text: str) -> list[str]:
    blob = re.sub(r"\s+", "", text)
    grams: list[str] = []
    for size in (4, 3, 2):
        if len(blob) < size:
            continue
        for index in range(len(blob) - size + 1):
            gram = blob[index : index + size]
            if gram in STOP_PHRASES:
                continue
            grams.append(gram)
    return grams


def _overlap_score(query: str, target: str) -> float:
    if not query or not target:
        return 0.0
    compact_q = re.sub(r"\s+", "", query)
    compact_t = re.sub(r"\s+", "", target)
    if compact_q and compact_q in compact_t:
        return 80.0 + min(len(compact_q), 20)
    score = 0.0
    seen: set[str] = set()
    for gram in _grams(query):
        if gram in seen:
            continue
        seen.add(gram)
        if gram in compact_t:
            score += float(len(gram))
    return score


def _rank_chunks(question: str, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
    query = _content_query(question)
    if not query.strip() or not chunks:
        return []
    df: dict[str, int] = {}
    for gram in {item for chunk in chunks for item in _grams(chunk.question)}:
        df[gram] = sum(1 for chunk in chunks if gram in chunk.question)
    total = max(len(chunks), 1)
    ranked: list[tuple[float, KnowledgeChunk]] = []
    for chunk in chunks:
        question_score = _overlap_score(query, chunk.question)
        answer_score = _overlap_score(query, chunk.text) * 0.35
        source_score = _overlap_score(query, chunk.source) * 1.2
        idf_bonus = 0.0
        for gram in set(_grams(query)):
            if gram in chunk.question:
                idf_bonus += math.log((total + 1) / (df.get(gram, 0) + 1)) * len(gram)
        score = question_score + answer_score + source_score + idf_bonus
        if score >= 4:
            ranked.append((score, chunk))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in ranked]


def _format_answer(question: str, text: str) -> str:
    body = text.strip()
    if len(body) > _MAX_ANSWER_CHARS:
        body = body[:_MAX_ANSWER_CHARS].rstrip() + "…"
    lead = question.strip().rstrip("？?")
    if lead and not body.startswith(lead):
        return f"{lead}：\n{body}"
    return body


def _snippet(text: str, limit: int) -> str:
    blob = re.sub(r"\s+", " ", text).strip()
    if len(blob) <= limit:
        return blob
    return blob[: limit - 1].rstrip() + "…"
