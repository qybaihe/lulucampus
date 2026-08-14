"""Observable quality of a living portrait — coverage, drift, recency."""

from __future__ import annotations

import math
from typing import Any

from portrait_evolve.portrait import Portrait


STAGES = ("prior_only", "calibrating", "converging", "living")


def lived_mass(portrait: Portrait) -> float:
    bags = (
        portrait.lived.domains,
        portrait.lived.scenes,
        portrait.lived.skills,
        portrait.lived.roles_offered,
    )
    return sum(item.mass for bag in bags for item in bag.values())


def infer_stage(portrait: Portrait) -> str:
    mass = lived_mass(portrait)
    if portrait.event_count <= 2 and mass < 0.8:
        return "prior_only"
    if mass < 2.2:
        return "calibrating"
    if portrait.confidence >= 0.62 and mass >= 4.0:
        return "living"
    return "converging"


def _l1(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    return sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys) / len(keys)


def measure(portrait: Portrait) -> dict[str, Any]:
    domains = portrait.lived.scores("domains")
    scenes = portrait.lived.scores("scenes")
    mass = lived_mass(portrait)
    active_domains = sum(1 for score in domains.values() if score >= 0.12)
    coverage = min(1.0, active_domains / 6.0)
    recency = 0.0
    stamps = [item.last_at for item in portrait.lived.domains.values() if item.last_at]
    if stamps:
        recency = 1.0
    taste_div = _l1(portrait.taste.scores("domains"), portrait.lived.scores("domains"))
    academic_share = sum(portrait.academic.scores("skills").values())
    lived_share = sum(portrait.lived.scores("skills").values())
    return {
        "stage": infer_stage(portrait),
        "lived_mass": round(mass, 4),
        "coverage": round(coverage, 4),
        "active_domains": active_domains,
        "active_scenes": sum(1 for score in scenes.values() if score >= 0.12),
        "taste_lived_l1": round(taste_div, 4),
        "behavior_over_prior": round(
            lived_share / (lived_share + academic_share + 1e-6), 4
        ),
        "recency_flag": recency,
        "entropy": _entropy(domains),
    }


def _entropy(scores: dict[str, float]) -> float:
    total = sum(max(0.0, value) for value in scores.values())
    if total <= 0:
        return 0.0
    probs = [value / total for value in scores.values() if value > 0]
    return round(-sum(p * math.log(p + 1e-12) for p in probs), 4)


STAGE_LABELS = {
    "prior_only": "冷启动先验",
    "calibrating": "行为校准中",
    "converging": "画像收敛中",
    "living": "活画像",
}
