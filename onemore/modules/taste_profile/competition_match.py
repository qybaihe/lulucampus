"""Score competitions against a Douyin taste persona (pure, no I/O).

Used by the competition list/detail and intent compile so a persona actually
changes ranking, copy, and "who to recruit" hints.
"""

from __future__ import annotations

from typing import Any

from onemore.modules.taste_profile.taxonomy import INTEREST_DOMAINS, TAG_DEFINITIONS

# Taste domain → competition capability keys (course tag space).
DOMAIN_TO_SKILLS: dict[str, tuple[str, ...]] = {
    "ai_programming": (
        "machine_learning",
        "backend",
        "frontend",
        "data_analysis",
        "algorithm",
    ),
    "tech_devices": ("backend", "frontend"),
    "gaming_strategy": ("product", "machine_learning", "algorithm"),
    "visual_creation": ("visual_design", "design", "video"),
    "music_literature": ("writing", "design", "presentation"),
    "career_growth": (
        "product",
        "business_analysis",
        "operations",
        "presentation",
        "writing",
    ),
    "knowledge_method": ("research", "writing", "data_analysis"),
    "finance_consumption": ("business_analysis", "data_analysis"),
    "health_sports": (),
    "travel_city": ("operations",),
    "relationship_family": (),
    "humor_pets": (),
}

SKILL_LABELS: dict[str, str] = {
    "frontend": "前端",
    "backend": "后端",
    "design": "设计",
    "visual_design": "视觉",
    "product": "产品",
    "data_analysis": "数据分析",
    "machine_learning": "机器学习",
    "algorithm": "算法",
    "presentation": "路演",
    "writing": "文案",
    "research": "调研",
    "video": "视频",
    "operations": "运营",
    "business_analysis": "商业分析",
}

_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    item.key: (item.label, *item.keywords[:12]) for item in INTEREST_DOMAINS
}
_TAG_LABELS: dict[str, str] = {item.key: item.label for item in TAG_DEFINITIONS}


def _norm(value: str) -> str:
    return "".join(str(value).lower().split())


def _label_of(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("label") or item.get("key") or "").strip()
    return str(item or "").strip()


def _key_of(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("key") or "").strip()
    return str(item or "").strip()


def _haystack(competition: dict[str, Any]) -> str:
    parts = [str(competition.get("name") or "")]
    parts.extend(str(track) for track in (competition.get("tracks") or []))
    for skill in competition.get("required_skills") or []:
        if isinstance(skill, dict):
            parts.append(str(skill.get("label") or skill.get("key") or ""))
        else:
            parts.append(str(skill))
    return _norm(" ".join(parts))


def _required_skill_keys(competition: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for skill in competition.get("required_skills") or []:
        key = skill.get("key") if isinstance(skill, dict) else skill
        text = str(key or "").strip()
        if text and text not in keys:
            keys.append(text)
    return keys


def _domain_weights(persona: dict[str, Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for domain in persona.get("interest_domains") or []:
        key = _key_of(domain)
        if not key:
            continue
        score = 0.5
        if isinstance(domain, dict):
            try:
                score = float(domain.get("score") or 0.5)
            except (TypeError, ValueError):
                score = 0.5
        weights[key] = max(weights.get(key, 0.0), min(score, 1.5))
    primary = persona.get("primary_tag") or {}
    primary_key = _key_of(primary)
    for tag in TAG_DEFINITIONS:
        if tag.key == primary_key:
            for domain_key, weight in tag.domains.items():
                weights[domain_key] = max(weights.get(domain_key, 0.0), min(weight / 3.0, 1.2))
    return weights


def _covered_skills(domain_weights: dict[str, float]) -> set[str]:
    covered: set[str] = set()
    for domain, weight in domain_weights.items():
        if weight < 0.25:
            continue
        covered.update(DOMAIN_TO_SKILLS.get(domain, ()))
    return covered


def score_competition(persona: dict[str, Any] | None, competition: dict[str, Any]) -> dict[str, Any]:
    """Return taste_fit fields to merge into a competition view."""
    empty = {
        "taste_fit": None,
        "taste_fit_label": None,
        "taste_fit_reasons": [],
        "recruit_hints": [],
    }
    if not persona:
        return empty

    domains = _domain_weights(persona)
    if not domains and not persona.get("primary_tag"):
        return empty

    haystack = _haystack(competition)
    required = _required_skill_keys(competition)
    covered = _covered_skills(domains)

    skill_hits: list[str] = []
    keyword_hits: list[str] = []
    score = 0.0

    for domain, weight in sorted(domains.items(), key=lambda item: item[1], reverse=True):
        mapped = DOMAIN_TO_SKILLS.get(domain, ())
        matched_skills = [key for key in mapped if key in required]
        if matched_skills:
            score += 0.28 * min(weight, 1.0)
            skill_hits.extend(matched_skills[:2])
        for keyword in _DOMAIN_KEYWORDS.get(domain, ()):
            token = _norm(keyword)
            if len(token) >= 2 and token in haystack:
                score += 0.12 * min(weight, 1.0)
                keyword_hits.append(keyword)
                break

    primary_label = _label_of(persona.get("primary_tag"))
    if primary_label:
        token = _norm(primary_label)
        if len(token) >= 2 and token in haystack:
            score += 0.18

    for facet in persona.get("interest_facets") or []:
        label = _label_of(facet)
        token = _norm(label)
        if len(token) >= 2 and token in haystack:
            score += 0.16
            keyword_hits.append(label)

    score = round(min(score, 1.0), 4)
    reasons: list[str] = []
    if primary_label:
        reasons.append(f"以你的「{primary_label}」画像来看")
    if keyword_hits:
        reasons.append(f"赛题方向对上了你的「{keyword_hits[0]}」")
    elif skill_hits:
        reasons.append(f"需要的{SKILL_LABELS.get(skill_hits[0], skill_hits[0])}和你的兴趣重合")

    label = None
    if score >= 0.55:
        label = "很适合你"
    elif score >= 0.32:
        label = "和你有点像"

    missing = [key for key in required if key not in covered]
    hints: list[str] = []
    if missing:
        names = [SKILL_LABELS.get(key, key) for key in missing[:3]]
        if len(names) == 1:
            hints.append(f"组队时建议再找会{names[0]}的人")
        else:
            hints.append(f"组队时建议补上：{'、'.join(names)}")
    elif required:
        hints.append("你的兴趣已经覆盖这赛的核心角色，找作息相近的人即可")
    for hint in (persona.get("matching_hints") or [])[:1]:
        text = str(hint).strip()
        if text and text not in hints:
            hints.append(text)

    return {
        "taste_fit": score,
        "taste_fit_label": label,
        "taste_fit_reasons": reasons[:3],
        "recruit_hints": hints[:3],
    }


def apply_taste_fit(
    views: list[dict[str, Any]], persona: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Annotate competition views and, when any fit exists, sort by it."""
    scored: list[dict[str, Any]] = []
    any_fit = False
    for view in views:
        payload = score_competition(persona, view)
        row = {**view, **payload}
        scored.append(row)
        if (payload.get("taste_fit") or 0) > 0:
            any_fit = True
    if not any_fit:
        return scored
    tier_rank = {"A": 0, "B": 1, "C": 2}
    scored.sort(
        key=lambda item: (
            -(item.get("taste_fit") or 0),
            tier_rank.get(str(item.get("recommendation_tier") or "B"), 9),
            -int(item.get("priority") or 0),
        )
    )
    return scored
