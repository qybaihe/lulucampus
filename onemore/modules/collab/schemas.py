from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from onemore.core.schemas import APIModel


class ImageMessageReference(APIModel):
    media_id: str = Field(min_length=36, max_length=36)
    caption: str | None = Field(default=None, max_length=500)


class ImageMessagePayload(APIModel):
    media_id: str
    url: str
    content_type: Literal["image/jpeg", "image/png", "image/heic", "image/heif"]
    byte_count: int
    sha256: str
    width: int | None = None
    height: int | None = None
    caption: str | None = None


class LocationMessagePayload(APIModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    label: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=300)


class MessageCreate(APIModel):
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    content_type: Literal["text", "image", "location"] = "text"
    image: ImageMessageReference | None = None
    location: LocationMessagePayload | None = None

    @model_validator(mode="after")
    def validate_typed_content(self) -> MessageCreate:
        valid = (
            self.content_type == "text" and self.content is not None and not self.image and not self.location
        ) or (
            self.content_type == "image" and self.image is not None and self.content is None and not self.location
        ) or (
            self.content_type == "location" and self.location is not None and self.content is None and not self.image
        )
        if not valid:
            raise ValueError("content_type 必须与唯一的 text、image 或 location 载荷一致")
        return self


class MessageView(APIModel):
    id: str
    channel_id: str
    sender_id: str
    sender_type: Literal["human", "azou", "system"]
    content_type: Literal["text", "image", "location"]
    content: str | None = None
    image: ImageMessagePayload | None = None
    location: LocationMessagePayload | None = None
    sent_at: datetime


class MentionAzouRequest(APIModel):
    text: str = Field(min_length=1, max_length=1000)


class MentionAzouResult(APIModel):
    message: MessageView
    action_hint: dict | None = None


class ChannelScenePolicyView(APIModel):
    mode: Literal["social", "sensitive_muted_onsite"]
    phase: Literal["always", "pre_arrival", "onsite_muted", "post_event"]
    sending_enabled: bool
    live_connection_enabled: bool
    reason: str | None
    next_change_at: datetime | None
    source: Literal["server_scene_policy"]


class SharedExperienceView(APIModel):
    id: str
    participants: list[str]
    gathering_type: str
    occurred_at: datetime
    outcome: Literal["completed", "interrupted"]
    common_grounds: list[str]


class RelationMilestoneView(APIModel):
    reached: int
    reached_label: str | None = None
    next: int | None = None
    next_label: str | None = None
    remaining: int | None = None


class RelationTimelineEntryView(APIModel):
    """双方可见的经历时间线条目：只记事实，禁止评分。"""

    gathering_id: str
    title: str | None = None
    gathering_type: str
    occurred_at: datetime
    location: str | None = None
    duration_minutes: int | None = None
    outcome: Literal["completed", "interrupted"]
    common_grounds: list[str] = Field(default_factory=list)
    via_recurrence: bool = False


class RelationNextWindowView(APIModel):
    start_at: datetime
    end_at: datetime


class RelationGoalSummaryView(APIModel):
    id: str
    definition: str
    current_value: float
    target_value: float
    unit: str
    period_end: date


class RelationView(APIModel):
    id: str
    participants: list[dict]
    status: str
    experiences: list[SharedExperienceView]
    latest_experience_at: datetime | None
    channel_id: str | None
    times_together: int = 0
    recur_count: int = 0
    is_fixed_partner: bool = False
    partner_title: str = "新搭子"
    milestone: RelationMilestoneView | None = None
    timeline: list[RelationTimelineEntryView] = Field(default_factory=list)
    next_window: RelationNextWindowView | None = None
    active_goal: RelationGoalSummaryView | None = None


class RecurRelationRequest(APIModel):
    gathering_type: str | None = Field(default=None, max_length=64)


class SharedGoalCreate(APIModel):
    definition: str = Field(min_length=1, max_length=500)
    period_start: date
    period_end: date
    target_value: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_period(self) -> SharedGoalCreate:
        if self.period_end <= self.period_start:
            raise ValueError("目标结束日期必须晚于开始日期")
        return self


class SharedGoalView(APIModel):
    class Milestone(APIModel):
        fraction: float
        target_value: float
        reached: bool
        reached_at: datetime | None = None

    class MemberProgress(APIModel):
        user_id: str
        display_name: str | None
        current_value: float
        last_progress_at: datetime | None

    id: str
    relation_id: str
    definition: str
    period_start: date
    period_end: date
    target_value: float
    current_value: float
    unit: str
    status: str
    milestones: list[Milestone] = Field(default_factory=list)
    member_progress: list[MemberProgress] = Field(default_factory=list)
    next_action: str | None = None
    last_broadcast: str | None = None
    last_progress_at: datetime | None = None
    progress_source: Literal["attendance_and_completion"] = "attendance_and_completion"


class SharedGoalUpdate(APIModel):
    next_action: str = Field(min_length=1, max_length=500)
