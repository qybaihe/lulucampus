from __future__ import annotations

from datetime import datetime

from pydantic import Field

from onemore.core.schemas import APIModel


class TimetableEntry(APIModel):
    course_id: str
    course_code: str
    course_name: str
    class_code: str
    start_at: datetime
    end_at: datetime
    location: str | None = None
    changed: bool = False
    title: str | None = None
    time_label: str | None = None
    display_code: str | None = None
    display_class_code: str | None = None


class TimetableView(APIModel):
    week: int
    entries: list[TimetableEntry]
    updated_at: datetime | None
    source: str = "cache"


class FreeWindowView(APIModel):
    start_at: datetime
    end_at: datetime
    campus: str | None
    stability: float


class IntersectionRequest(APIModel):
    user_ids: list[str] = Field(min_length=2, max_length=20)
    start_after: datetime | None = None
    end_before: datetime | None = None
    minimum_minutes: int = Field(default=60, ge=15, le=480)


class IntersectionView(APIModel):
    start_at: datetime
    end_at: datetime
    feasible_count: int
    stability: float
    campus_reachable: bool
