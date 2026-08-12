from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from onemore.core.schemas import APIModel
from onemore.core.time import ensure_utc


class QuotaBatch(APIModel):
    label: str = Field(min_length=1, max_length=80)
    slots: int = Field(ge=1, le=500)


class OfficialGatheringCreate(APIModel):
    title: str = Field(min_length=2, max_length=256)
    goal: str = Field(min_length=2, max_length=500)
    gathering_type: str = Field(min_length=1, max_length=64)
    start_at: datetime
    end_at: datetime
    location: str = Field(min_length=1, max_length=256)
    campus: str | None = Field(default=None, max_length=64)
    min_size: int = Field(default=3, ge=2, le=500)
    target_size: int = Field(default=20, ge=2, le=500)
    required_roles: list[str] = Field(default_factory=list, max_length=20)
    quota_batches: list[QuotaBatch] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_official_gathering(self) -> OfficialGatheringCreate:
        if ensure_utc(self.end_at) <= ensure_utc(self.start_at):
            raise ValueError("结束时间必须晚于开始时间")
        if self.min_size > self.target_size:
            raise ValueError("最低人数不能超过目标人数")
        if sum(item.slots for item in self.quota_batches) > self.target_size:
            raise ValueError("批量名额合计不能超过目标人数")
        return self


class OfficialTemplateCreate(APIModel):
    title: str = Field(min_length=2, max_length=256)
    goal: str = Field(min_length=2, max_length=500)
    gathering_type: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=256)
    campus: str | None = Field(default=None, max_length=64)
    min_size: int = Field(default=3, ge=2, le=500)
    target_size: int = Field(default=20, ge=2, le=500)
    duration_minutes: int = Field(default=120, ge=30, le=1440)
    required_roles: list[str] = Field(default_factory=list, max_length=20)
    recurrence_rule: str | None = Field(default=None, max_length=128)


class OfficialTemplatePatch(APIModel):
    title: str | None = Field(default=None, min_length=2, max_length=256)
    goal: str | None = Field(default=None, min_length=2, max_length=500)
    gathering_type: str | None = Field(default=None, min_length=1, max_length=64)
    location: str | None = Field(default=None, min_length=1, max_length=256)
    campus: str | None = Field(default=None, max_length=64)
    min_size: int | None = Field(default=None, ge=2, le=500)
    target_size: int | None = Field(default=None, ge=2, le=500)
    duration_minutes: int | None = Field(default=None, ge=30, le=1440)
    required_roles: list[str] | None = Field(default=None, max_length=20)
    recurrence_rule: str | None = Field(default=None, max_length=128)


class OfficialTemplateCopy(APIModel):
    title: str | None = Field(default=None, min_length=2, max_length=256)


class OfficialTemplateView(OfficialTemplateCreate):
    id: str
    active: bool
    created_at: datetime
    updated_at: datetime


class TemplateInstantiate(APIModel):
    start_at: datetime
    quota_batches: list[QuotaBatch] = Field(default_factory=list, max_length=20)


class OrganizerVerification(APIModel):
    verified: bool


class OfficialGatheringSummaryView(APIModel):
    id: str
    title: str
    status: str
    start_at: datetime | None
    target_size: int


class OfficialGatheringCreatedView(APIModel):
    id: str
    status: str
    is_official: bool = True


class OrganizerGatheringStatusView(APIModel):
    id: str
    status: str


class OrganizerParticipantView(APIModel):
    user_id: str
    display_name: str | None
    confirmation_status: str
    attended: bool


class OrganizerDashboardView(APIModel):
    gathering_id: str
    status: str
    target_size: int
    registered_count: int
    confirmed_count: int
    attended_count: int
    quota_batches: list[QuotaBatch]
    participants: list[OrganizerParticipantView] | None
    identity_visibility: str


class OrganizerAttendanceView(APIModel):
    user_id: str
    attended: bool
