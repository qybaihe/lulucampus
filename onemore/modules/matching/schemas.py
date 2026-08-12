from __future__ import annotations

from onemore.core.schemas import APIModel


class MatchingRunResult(APIModel):
    examined: int
    formed: int
    gathering_ids: list[str]


class MatchExplanation(APIModel):
    score: float
    dimensions: dict[str, float]
    reason: str
