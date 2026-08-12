from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from onemore.core.schemas import APIModel


class UnlockView(APIModel):
    """Internal capability gate. Prefer benefits/conditions for client UI."""

    capability: str
    required_level: str
    unlocked: bool


class TrustMetricProgressView(APIModel):
    key: str
    label: str
    current: float
    required: float
    unit: str


class TrustConditionView(APIModel):
    """One structured condition toward the next trust level."""

    key: str
    label: str
    met: bool
    current: float | None = None
    required: float | None = None
    unit: str | None = None
    detail: str | None = None


class TrustLevelGuideItem(APIModel):
    """Handbook entry for the upgrade document sheet."""

    level: str
    name: str
    how: str
    benefits: list[str] = Field(default_factory=list)
    is_current: bool = False
    is_reached: bool = False


class TrustProgressView(APIModel):
    level: str
    level_name: str
    level_narrative: str | None = None
    next_level: str | None
    next_level_name: str | None = None
    next_level_progress: list[TrustMetricProgressView] = Field(default_factory=list)
    conditions: list[TrustConditionView] = Field(default_factory=list)
    current_benefits: list[str] = Field(default_factory=list)
    next_benefits: list[str] = Field(default_factory=list)
    overall_progress: float = 0.0
    level_guide: list[TrustLevelGuideItem] = Field(default_factory=list)
    gaps: list[str]
    statistics: dict
    unlocks: list[UnlockView]
    observation: dict | None = None


class AppealCreate(APIModel):
    reason: str = Field(min_length=10, max_length=1000)


class AppealView(APIModel):
    id: str
    reason: str
    status: str
    result: str | None = None
    created_at: datetime
    updated_at: datetime
    decided_at: datetime | None = None


class AppealResolution(APIModel):
    status: Literal["approved", "rejected"]
    result: str = Field(min_length=2, max_length=2000)
