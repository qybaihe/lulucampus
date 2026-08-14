"""Match two living portraits: similar taste, complementary roles."""

from __future__ import annotations

import math
from typing import Any

from portrait_evolve.portrait import Portrait
from portrait_evolve.taxonomy import label_of


def _blend(portrait: Portrait, field_name: str) -> dict[str, float]:
    blended: dict[str, float] = {}
    for weight, layer in (
        (0.25, portrait.academic),
        (0.30, portrait.taste),
        (0.45, portrait.lived),
    ):
        for key, score in layer.scores(field_name).items():
            blended[key] = blended.get(key, 0.0) + weight * score
    return blended


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    dot = sum(left.get(key, 0.0) * right.get(key, 0.0) for key in keys)
    n1 = math.sqrt(sum(value * value for value in left.values()))
    n2 = math.sqrt(sum(value * value for value in right.values()))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _active(scores: dict[str, float], floor: float = 0.12) -> set[str]:
    return {key for key, score in scores.items() if score >= floor}


def complement(offered: set[str], sought: set[str]) -> float:
    if not sought:
        return 0.0
    return len(offered & sought) / len(sought)


def score_pair(left: Portrait, right: Portrait) -> dict[str, Any]:
    domains = _cosine(_blend(left, "domains"), _blend(right, "domains"))
    skills = _cosine(_blend(left, "skills"), _blend(right, "skills"))
    scenes = _jaccard(
        _active(left.lived.scores("scenes")),
        _active(right.lived.scores("scenes")),
    )
    left_offered = _active(left.lived.scores("roles_offered"))
    right_offered = _active(right.lived.scores("roles_offered"))
    left_sought = _active(left.lived.scores("roles_sought"))
    right_sought = _active(right.lived.scores("roles_sought"))
    cover = 0.5 * (
        complement(left_offered, right_sought) + complement(right_offered, left_sought)
    )
    peer = 0.0
    if right.user_id in left.peers:
        peer = min(1.0, left.peers[right.user_id].score)
    elif left.user_id in right.peers:
        peer = min(1.0, right.peers[left.user_id].score)

    total = (
        0.40 * domains
        + 0.18 * skills
        + 0.14 * scenes
        + 0.20 * cover
        + 0.08 * peer
    )
    reasons: list[str] = []
    shared_domains = _active(_blend(left, "domains")) & _active(_blend(right, "domains"))
    if shared_domains:
        labels = "、".join(label_of("domain", key) for key in list(shared_domains)[:2])
        reasons.append(f"兴趣域重叠：{labels}")
    if cover >= 0.34:
        reasons.append("一方会的，正好是另一方在找的")
    if scenes >= 0.4:
        reasons.append("打过同一类局")
    if peer >= 0.3:
        reasons.append("已经一起成过局")
    if not reasons:
        reasons.append("共同时间与目标还要对上，画像本身只是弱信号")

    return {
        "score": round(min(1.0, total), 4),
        "parts": {
            "domains": round(domains, 4),
            "skills": round(skills, 4),
            "scenes": round(scenes, 4),
            "complement": round(cover, 4),
            "peer": round(peer, 4),
        },
        "reasons": reasons[:3],
        "mode": "complementary" if cover >= 0.34 else "similar",
    }
