"""Taste analysis: content baseline, optional LLM polish, domain refinement quiz.

Scoring is deterministic and offline. An optional LLM call may rewrite the
human-readable summary and propose interest facets; it never decides whether a
user belongs to a tag family. Quiz answers only refine already-detected
domains / expression style (calibrated=true).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from statistics import mean
from typing import Any

from onemore.modules.taste_profile.taxonomy import (
    BEHAVIOR_SIGNALS,
    INTEREST_DOMAINS,
    QUESTION_BANK,
    REFINEMENT_OUTCOME_QUESTION,
    REFINEMENT_QUESTION_BANK,
    TAG_DEFINITIONS,
    TAG_GROUPS,
    question_by_id,
    tag_by_key,
)

MODEL_VERSION = "taste-v2"
SAMPLE_FULL_THRESHOLD = 200
RECENT_WINDOW = 200
# Quiz answers only nudge scores; content remains the source of truth.
REFINE_TAG_SCALE = 0.08
REFINE_DOMAIN_SCALE = 0.12
REFINE_DIMENSION_SCALE = 0.10
MIN_DOMAIN_SCORE_FOR_QUESTION = 0.02

IMAGE_POST_TYPES = {2, 68, 150}


@dataclass
class ContentAnalysis:
    item_count: int
    content_scores: dict[str, float] = field(default_factory=dict)
    dimensions: dict[str, float] = field(default_factory=dict)
    domain_shares: dict[str, float] = field(default_factory=dict)
    recent200_domains: dict[str, float] = field(default_factory=dict)
    top_domains: list[dict[str, Any]] = field(default_factory=list)
    sample_stats: dict[str, Any] = field(default_factory=dict)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def _as_seconds(value: Any) -> float | None:
    if isinstance(value, (int, float)) and value:
        duration = float(value)
        return round(duration / 1000, 1) if duration > 1000 else round(duration, 1)
    return None


def _published_at(raw: dict[str, Any]) -> str | None:
    created = raw.get("create_time")
    if not isinstance(created, (int, float)) or not created:
        return None
    return datetime.fromtimestamp(created, tz=timezone(timedelta(hours=8))).isoformat()


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize one raw aweme payload into the compact persisted record."""
    aweme_id = str(raw.get("aweme_id") or "")
    images = raw.get("images") or raw.get("image_post_info")
    is_image = bool(images) or raw.get("aweme_type") in IMAGE_POST_TYPES
    kind = "note" if is_image else "video"
    author = raw.get("author") or {}
    stats = raw.get("statistics") or {}
    video = raw.get("video") or {}
    description = str(raw.get("desc") or raw.get("item_title") or "").strip()
    hashtags = [
        entry.get("hashtag_name")
        for entry in (raw.get("text_extra") or [])
        if entry.get("hashtag_name")
    ]
    platform_tags = [
        entry.get("tag_name")
        for entry in (raw.get("video_tag") or [])
        if entry.get("tag_name")
    ]
    return {
        "aweme_id": aweme_id,
        "kind": kind,
        "url": f"https://www.douyin.com/{kind}/{aweme_id}",
        "title": str(raw.get("item_title") or ""),
        "description": description,
        "hashtags": hashtags,
        "platform_tags": platform_tags,
        "author": {
            "nickname": str(author.get("nickname") or ""),
            "uid": str(author.get("uid") or ""),
            "sec_uid": str(author.get("sec_uid") or ""),
        },
        "published_at": _published_at(raw),
        "duration_seconds": _as_seconds(video.get("duration") or raw.get("duration")),
        "statistics": {
            "likes": int(stats.get("digg_count") or 0),
            "comments": int(stats.get("comment_count") or 0),
            "collects": int(stats.get("collect_count") or 0),
            "shares": int(stats.get("share_count") or 0),
        },
        "is_aigc": bool(raw.get("is_aigc_media") or False),
    }


def item_text(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("description") or ""),
        str(item.get("title") or ""),
        str((item.get("author") or {}).get("nickname") or ""),
    ]
    parts.extend(str(tag) for tag in item.get("hashtags") or [])
    parts.extend(str(tag) for tag in item.get("platform_tags") or [])
    return " ".join(parts).lower()


def _keyword_hits(texts: list[str], keywords: tuple[str, ...]) -> int:
    return sum(1 for text in texts if any(word in text for word in keywords))


def _domain_shares(texts: list[str]) -> dict[str, float]:
    total = len(texts) or 1
    return {
        domain.key: round(_keyword_hits(texts, domain.keywords) / total, 4)
        for domain in INTEREST_DOMAINS
    }


def _signal_shares(texts: list[str]) -> dict[str, float]:
    total = len(texts) or 1
    return {
        signal.key: round(_keyword_hits(texts, signal.keywords) / total, 4)
        for signal in BEHAVIOR_SIGNALS
    }


def _breadth(domain_shares: dict[str, float]) -> float:
    top_values = sorted(domain_shares.values(), reverse=True)[:4]
    mean_top = mean(top_values) if top_values else 0.0
    coverage = sum(1 for share in domain_shares.values() if share >= 0.02) / len(domain_shares)
    return round(_clamp(mean_top * 0.7 + coverage * 0.3), 4)


def _tag_content_scores(
    domain_shares: dict[str, float], signal_shares: dict[str, float], breadth: float
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for tag in TAG_DEFINITIONS:
        domain_part = sum(domain_shares.get(key, 0.0) * weight for key, weight in tag.domains.items())
        signal_part = sum(signal_shares.get(key, 0.0) * weight for key, weight in tag.signals.items())
        breadth_part = breadth * tag.breadth
        weight_total = sum(tag.domains.values()) + sum(tag.signals.values()) + tag.breadth
        scores[tag.key] = (
            round((domain_part + signal_part + breadth_part) / weight_total, 4) if weight_total else 0.0
        )
    return scores


def _blended_domain_shares(
    domain_shares: dict[str, float], recent_domain_shares: dict[str, float], item_count: int
) -> dict[str, float]:
    if item_count < SAMPLE_FULL_THRESHOLD:
        return domain_shares
    return {
        key: round(_clamp(0.7 * share + 0.3 * recent_domain_shares.get(key, 0.0)), 4)
        for key, share in domain_shares.items()
    }


def analyze_content(items: list[dict[str, Any]], *, api_pages: int = 0) -> ContentAnalysis:
    texts = [item_text(item) for item in items]
    recent_texts = texts[:RECENT_WINDOW]
    domain_shares = _domain_shares(texts)
    recent_domain_shares = _domain_shares(recent_texts)
    signal_shares = _signal_shares(texts)
    blended = _blended_domain_shares(domain_shares, recent_domain_shares, len(items))
    breadth = _breadth(blended)
    content_scores = _tag_content_scores(blended, signal_shares, breadth)
    top_domains = [
        {
            "key": domain.key,
            "label": domain.label,
            "score": blended[domain.key],
        }
        for domain in sorted(
            INTEREST_DOMAINS,
            key=lambda item: blended.get(item.key, 0.0),
            reverse=True,
        )
        if blended.get(domain.key, 0.0) > 0.0
    ][:4]
    dimensions = {
        "openness": breadth,
        "action_orientation": signal_shares.get("action_oriented", 0.0),
        "aesthetic_orientation": signal_shares.get("aesthetic", 0.0),
        "competition_orientation": signal_shares.get("competitive", 0.0),
    }
    authors = {
        (item.get("author") or {}).get("sec_uid") or (item.get("author") or {}).get("nickname")
        for item in items
    }
    authors.discard("")
    sample_stats = {
        "items": len(items),
        "unique_authors": len(authors),
        "api_pages": api_pages,
    }
    return ContentAnalysis(
        item_count=len(items),
        content_scores=content_scores,
        dimensions=dimensions,
        domain_shares=blended,
        recent200_domains=recent_domain_shares,
        top_domains=top_domains,
        sample_stats=sample_stats,
    )


def _rank_tags(scores: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


def _pick_secondary(
    ranked: list[tuple[str, float]], primary_key: str
) -> list[dict[str, Any]]:
    primary_group = TAG_GROUPS.get(primary_key, "other")
    secondary: list[dict[str, Any]] = []
    used_groups: set[str] = set()
    for key, score in ranked[1:]:
        group = TAG_GROUPS.get(key, "other")
        if group == primary_group or group in used_groups:
            continue
        if score < 0.05:
            continue
        secondary.append({"key": key, "label": _tag_label(key), "score": score})
        used_groups.add(group)
        if len(secondary) == 3:
            break
    if len(secondary) < 2:
        for key, score in ranked[1:]:
            if len(secondary) >= 2:
                break
            if all(item["key"] != key for item in secondary) and score >= 0.05:
                secondary.append({"key": key, "label": _tag_label(key), "score": score})
    return secondary


def _content_confidence(
    analysis: ContentAnalysis, primary_score: float, margin: float
) -> float:
    sufficiency = min(1.0, analysis.item_count / SAMPLE_FULL_THRESHOLD)
    margin_norm = min(1.0, margin / 0.12)
    strength = min(1.0, primary_score / 0.35)
    return round(_clamp(0.40 * sufficiency + 0.30 * margin_norm + 0.30 * strength), 4)


def _build_summary(
    primary_label: str,
    dimensions: dict[str, float],
    interest_domains: list[dict[str, Any]],
    interest_facets: list[dict[str, Any]] | None = None,
) -> str:
    traits: list[str] = []
    if dimensions.get("action_orientation", 0.0) >= 0.08:
        traits.append("偏实践与工具向")
    if dimensions.get("openness", 0.0) >= 0.15:
        traits.append("兴趣面较广")
    if dimensions.get("aesthetic_orientation", 0.0) >= 0.08:
        traits.append("有审美与氛围偏好")
    if dimensions.get("competition_orientation", 0.0) >= 0.08:
        traits.append("关注成长与挑战")
    if not traits:
        traits.append("口味较均衡")

    if interest_facets:
        focus = [
            str(item.get("label") or item.get("facet") or "")
            for item in interest_facets[:3]
            if item.get("label") or item.get("facet")
        ]
    else:
        focus = [str(domain.get("label") or "") for domain in interest_domains[:3] if domain.get("label")]
    focus = [item for item in focus if item]
    if len(focus) >= 2:
        center = f"{'、'.join(focus[:2])}，并延伸到{focus[2]}" if len(focus) >= 3 else "、".join(focus)
    elif focus:
        center = focus[0]
    else:
        center = "多元内容"

    return (
        f"更像一位{primary_label}：{ '，'.join(traits) }。"
        f"内容重心集中在{center}，适合作为匹配与成局的兴趣线索。"
    )


def _assemble_result(
    analysis: ContentAnalysis,
    scores: dict[str, float],
    dimensions: dict[str, float],
    *,
    calibrated: bool,
    interest_facets: list[dict[str, Any]] | None = None,
    calibrated_at: str | None = None,
) -> dict[str, Any]:
    ranked = _rank_tags(scores)
    primary_key, primary_score = ranked[0]
    margin = primary_score - ranked[1][1] if len(ranked) > 1 else 1.0
    primary_tag: dict[str, Any] = {
        "key": primary_key,
        "label": _tag_label(primary_key),
        "score": primary_score,
    }
    secondary = _pick_secondary(ranked, primary_key)
    interest_domains = analysis.top_domains
    facets = interest_facets or []
    confidence = _content_confidence(analysis, primary_score, margin)
    if calibrated:
        confidence = round(_clamp(confidence + 0.06), 4)
    summary = _build_summary(primary_tag["label"], dimensions, interest_domains, facets)
    sample = {
        **analysis.sample_stats,
        "calibrated": calibrated,
        "calibrated_at": calibrated_at,
        "interest_facets": facets,
        "generation": "rule",
    }
    return {
        "primary_tag": primary_tag,
        "secondary_tags": secondary,
        "interest_domains": interest_domains,
        "dimensions": {key: round(value, 4) for key, value in dimensions.items()},
        "summary": summary,
        "confidence": confidence,
        "sample": sample,
        "interest_facets": facets,
        "calibrated": calibrated,
        "calibrated_at": calibrated_at,
        "source": "douyin",
        "model_version": MODEL_VERSION,
        "visibility": "members",
    }


def build_provisional_result(
    analysis: ContentAnalysis,
    *,
    items: list[dict[str, Any]] | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Content-only profile ready for immediate use (calibrated=false)."""
    result = _assemble_result(
        analysis,
        dict(analysis.content_scores),
        dict(analysis.dimensions),
        calibrated=False,
        interest_facets=[],
        calibrated_at=None,
    )
    if use_llm and items:
        try:
            from onemore.modules.taste_profile.llm_enrich import enrich_provisional_profile

            result = enrich_provisional_profile(result, items)
        except Exception:
            result.setdefault("sample", {})
            result["sample"]["generation"] = "rule"
    return result


def select_questions(analysis: ContentAnalysis) -> list[dict[str, Any]]:
    """Pick 3–5 domain refinement questions from the strongest interest domains."""
    by_domain = {question.target_domain: question for question in REFINEMENT_QUESTION_BANK}
    selected: list[dict[str, Any]] = []
    used: set[str] = set()

    def append_question(question) -> None:
        if question.id in used:
            return
        selected.append(
            {
                "id": question.id,
                "type": "single_choice",
                "prompt": question.prompt,
                "required": True,
                "options": [
                    {"id": option.id, "label": option.label} for option in question.options
                ],
            }
        )
        used.add(question.id)

    ranked_domains = sorted(
        analysis.domain_shares.items(), key=lambda pair: pair[1], reverse=True
    )
    for key, score in ranked_domains:
        if score < MIN_DOMAIN_SCORE_FOR_QUESTION:
            continue
        question = by_domain.get(key)
        if question is None:
            continue
        append_question(question)
        if len(selected) >= 4:
            break

    if REFINEMENT_OUTCOME_QUESTION.id not in used and len(selected) < 5:
        append_question(REFINEMENT_OUTCOME_QUESTION)

    # Guarantee 3–5 questions even on sparse samples.
    if len(selected) < 3:
        for question in REFINEMENT_QUESTION_BANK:
            if len(selected) >= 3:
                break
            append_question(question)
    if len(selected) < 3:
        for question in QUESTION_BANK:
            if len(selected) >= 3:
                break
            append_question(question)
    return selected[:5]


def score_answers(
    analysis: ContentAnalysis,
    questions: list[dict[str, Any]],
    answers: list[dict[str, str]],
) -> dict[str, Any]:
    """Refine an existing content profile; never cross-validate tag membership."""
    scores = dict(analysis.content_scores)
    dimensions = dict(analysis.dimensions)
    domain_shares = dict(analysis.domain_shares)
    interest_facets: list[dict[str, Any]] = []
    top_tag_keys = {key for key, _ in _rank_tags(scores)[:4]}

    for answer in answers:
        question_id = answer.get("question_id")
        option_id = answer.get("option_id")
        question = question_by_id(question_id or "")
        if question is None or option_id not in {option.id for option in question.options}:
            raise ValueError(f"invalid answer: {question_id or ''}/{option_id or ''}")
        option = next(option for option in question.options if option.id == option_id)

        for key, delta in option.tag_delta.items():
            # Only nudge tags already present in the content baseline, or weak
            # in-domain siblings of the top family — never invent a new persona.
            baseline = analysis.content_scores.get(key, 0.0)
            if key not in top_tag_keys and baseline < 0.05:
                continue
            scores[key] = round(_clamp(scores.get(key, 0.0) + delta * REFINE_TAG_SCALE), 4)

        for key, delta in option.dimension_delta.items():
            dimensions[key] = round(
                _clamp(dimensions.get(key, 0.0) + delta * REFINE_DIMENSION_SCALE), 4
            )

        for key, delta in option.domain_delta.items():
            if domain_shares.get(key, 0.0) < MIN_DOMAIN_SCORE_FOR_QUESTION and key not in {
                item["key"] for item in analysis.top_domains
            }:
                continue
            domain_shares[key] = round(
                _clamp(domain_shares.get(key, 0.0) + delta * REFINE_DOMAIN_SCALE), 4
            )

        if option.facet_key:
            interest_facets.append(
                {
                    "domain": question.target_domain or "outcome",
                    "facet": option.facet_key,
                    "label": option.facet_label or option.label,
                    "source": "quiz",
                    "question_id": question.id,
                }
            )

    # Keep top_domains ordered by refined domain shares when answers touched them.
    refined_top = [
        {
            "key": domain.key,
            "label": domain.label,
            "score": domain_shares.get(domain.key, 0.0),
        }
        for domain in sorted(
            INTEREST_DOMAINS,
            key=lambda item: domain_shares.get(item.key, 0.0),
            reverse=True,
        )
        if domain_shares.get(domain.key, 0.0) > 0.0
    ][:4]
    refined_analysis = ContentAnalysis(
        item_count=analysis.item_count,
        content_scores=scores,
        dimensions=dimensions,
        domain_shares=domain_shares,
        recent200_domains=analysis.recent200_domains,
        top_domains=refined_top or analysis.top_domains,
        sample_stats=analysis.sample_stats,
    )
    calibrated_at = datetime.now(UTC).isoformat()
    return _assemble_result(
        refined_analysis,
        scores,
        dimensions,
        calibrated=True,
        interest_facets=interest_facets,
        calibrated_at=calibrated_at,
    )


def _tag_label(key: str) -> str:
    tag = tag_by_key(key)
    return tag.label if tag is not None else key
