"""Competition recommendation tier catalog (user-facing labels).

Storage remains the stable codes A / B / C on ``CompetitionEvent.recommendation_tier``.
Labels and short descriptions are derived here so the API never forces clients to
hard-code English ``Tier A`` wording.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RecommendationTier(StrEnum):
    """Stable storage / filter codes. Do not change without a data migration."""

    A = "A"
    B = "B"
    C = "C"


@dataclass(frozen=True, slots=True)
class RecommendationTierMeta:
    code: str
    label: str
    description: str
    """Short user-facing line for filter chips and detail footnotes."""

    sort_order: int
    """Lower first in filter UI (A → B → C)."""


# Canonical user-facing copy (方案一). Single source of truth for API + ingest docs.
RECOMMENDATION_TIERS: dict[str, RecommendationTierMeta] = {
    RecommendationTier.A.value: RecommendationTierMeta(
        code="A",
        label="优先推荐",
        description="学校或权威学会/行业组织官方通知，关键行动字段完整，默认优先展示。",
        sort_order=0,
    ),
    RecommendationTier.B.value: RecommendationTierMeta(
        code="B",
        label="可报名",
        description="官方赛项页可核验，信息仍可能变动；正常展示，临近报名可再核对。",
        sort_order=1,
    ),
    RecommendationTier.C.value: RecommendationTierMeta(
        code="C",
        label="补充参考",
        description="事实可核验，多为商业主办或推荐价值较弱；作补充信息，默认降权。",
        sort_order=2,
    ),
}

VALID_RECOMMENDATION_TIERS = frozenset(RECOMMENDATION_TIERS)
RECOMMENDATION_TIER_PATTERN = "^[ABC]$"
DEFAULT_RECOMMENDATION_TIER = RecommendationTier.B.value


def resolve_recommendation_tier(code: str | None) -> RecommendationTierMeta:
    """Map a stored code to display meta; unknown values fall back to B."""
    if code and code in RECOMMENDATION_TIERS:
        return RECOMMENDATION_TIERS[code]
    return RECOMMENDATION_TIERS[DEFAULT_RECOMMENDATION_TIER]


def recommendation_tier_catalog() -> list[RecommendationTierMeta]:
    """Filter-bar ordered catalog for clients."""
    return sorted(RECOMMENDATION_TIERS.values(), key=lambda item: item.sort_order)


def recommendation_fields(code: str | None) -> dict[str, str]:
    """Fields to merge into CompetitionView payloads."""
    meta = resolve_recommendation_tier(code)
    return {
        "recommendation_tier": meta.code,
        "recommendation_label": meta.label,
        "recommendation_description": meta.description,
    }
