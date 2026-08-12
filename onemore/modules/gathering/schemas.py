from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from onemore.core.schemas import APIModel
from onemore.core.time import ensure_utc


class ParticipantView(APIModel):
    user_id: str
    display_name: str | None
    college: str | None
    major: str | None
    role: str | None
    # Douyin / interest chips visible after identity disclosure.
    interest_tags: list[str] = Field(default_factory=list)
    taste_summary: str | None = None


class RecurrenceDecisionView(APIModel):
    decision: str
    kept_user_ids: list[str] = Field(default_factory=list)
    clone_gathering_id: str | None = None


class LeaveCapabilityView(APIModel):
    enabled: bool
    trust_impact: str
    message: str
    late_exit_cutoff: datetime | None = None
    server_now: datetime
    disabled_reason: str | None = None


class DepartedSafetyContextView(APIModel):
    gathering_id: str
    title: str
    gathering_type: str
    status: str
    left_at: datetime
    reportable_participants: list[ParticipantView] = Field(default_factory=list)


class GatheringView(APIModel):
    id: str
    title: str
    goal: str
    mood_note: str | None = None
    gathering_type: str
    mode: str
    status: str
    campus: str | None
    same_gender_only: bool
    identity_disclosure: str
    start_at: datetime | None
    end_at: datetime | None
    location: str | None
    target_size: int
    required_trust_level: str
    required_roles: list[str]
    match_reason: str | None = None
    looking_for: list[str] = Field(default_factory=list)
    my_confirmation: str | None = None
    confirmed_count: int | None = None
    member_count: int | None = None
    participants: list[ParticipantView] | None = None
    reportable_participants: list[ParticipantView] = Field(default_factory=list)
    my_recurrence_decision: RecurrenceDecisionView | None = None
    leave_capability: LeaveCapabilityView | None = None
    channel_id: str | None = None
    action_id: str | None = None
    expires_at: datetime | None


class InitiateGatheringRequest(APIModel):
    """T2 self-initiation path, intentionally distinct from an intent card."""

    title: str = Field(min_length=2, max_length=256)
    goal: str = Field(min_length=2, max_length=500)
    gathering_type: str = Field(min_length=1, max_length=64)
    mode: str = Field(default="similar", pattern="^(similar|complementary)$")
    campus: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=256)
    start_at: datetime | None = None
    end_at: datetime | None = None
    min_size: int = Field(default=3, ge=2, le=20)
    target_size: int = Field(default=4, ge=2, le=20)
    required_roles: list[str] = Field(default_factory=list, max_length=20)
    cross_college: bool = False

    @model_validator(mode="after")
    def validate_initiation(self) -> InitiateGatheringRequest:
        if self.min_size > self.target_size:
            raise ValueError("最低人数不能超过目标人数")
        if (self.start_at is None) != (self.end_at is None):
            raise ValueError("开始和结束时间必须同时提供")
        if self.start_at and self.end_at and ensure_utc(self.end_at) <= ensure_utc(self.start_at):
            raise ValueError("结束时间必须晚于开始时间")
        return self


class RecurringGatheringRequest(APIModel):
    """Create a server-owned weekly fixed series from a completed gathering."""

    first_start_at: datetime
    occurrences: int = Field(default=4, ge=2, le=12)
    interval_weeks: int = Field(default=1, ge=1, le=4)
    duration_minutes: int | None = Field(default=None, ge=30, le=1440)


class BackfillOpportunityView(APIModel):
    class FallbackOption(APIModel):
        key: str
        title: str
        summary: str
        min_size: int
        target_size: int
        location: str | None = None

    gathering_id: str
    open: bool
    fast_lane_active: bool
    fast_lane_until: datetime | None
    viewer_fast_lane_eligible: bool
    viewer_has_matching_intent: bool
    claim_available_at: datetime | None
    history_visible: bool = False
    viewer_is_member: bool
    fallback_options: list[FallbackOption] = Field(default_factory=list)


class BackfillClaimRequest(APIModel):
    role: str | None = Field(default=None, max_length=64)


class BackfillFallbackRequest(APIModel):
    option_key: str = Field(min_length=1, max_length=64)


class GapShareView(APIModel):
    """Public, identity-free payload carried by an opaque signed share token."""

    share_token: str
    gathering_id: str
    gathering_type: str
    title: str
    goal: str
    mood_note: str | None = None
    status: str
    campus: str | None
    start_at: datetime | None = None
    end_at: datetime | None = None
    target_size: int
    missing_count: int
    expires_at: datetime | None
    joinable: bool
    deep_link: str
    universal_link: str
    looking_for: list[str] = Field(default_factory=list)


class IcebreakerFactView(APIModel):
    kind: str
    text: str


class IcebreakerNextStepsView(APIModel):
    start_at: datetime | None
    end_at: datetime | None
    location: str | None
    campus: str | None
    channel_id: str | None
    checklist: list[str] = Field(default_factory=list)


class IcebreakerView(APIModel):
    """成局后 30 秒破冰包：全部来自既有事实，不新增评价字段。"""

    gathering_id: str
    headline: str
    facts: list[IcebreakerFactView]
    first_lines: list[str]
    next_steps: IcebreakerNextStepsView


class RecapTopPartnerView(APIModel):
    display_name: str | None
    times_together: int


class RecapTypeCountView(APIModel):
    gathering_type: str
    count: int


class SemesterRecapView(APIModel):
    """学期成局回忆录：服务端事实聚合，share_text 不含他人身份。"""

    term_label: str
    since: datetime
    gatherings_completed: int
    partners_met: int
    total_hours: float
    recurrences: int
    top_partner: RecapTopPartnerView | None = None
    top_types: list[RecapTypeCountView] = Field(default_factory=list)
    top_location: str | None = None
    highlights: list[str] = Field(default_factory=list)
    share_text: str


class PendingActionModificationView(APIModel):
    action_id: str
    reason: str
    proposed_params: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class GatheringActionCapabilityView(APIModel):
    """Server-authoritative campus action and its validated parameters."""

    enabled: bool
    action: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    disabled_reason: str | None = None
    pending_modification: PendingActionModificationView | None = None


class GatheringBookingOptionView(APIModel):
    """Short-lived, server-signed room/gym option returned by Hermes."""

    option_token: str
    resource_type: str
    action: str
    location: str
    start_at: datetime
    end_at: datetime
    label: str


class GatheringBookingPlanRequest(APIModel):
    option_token: str = Field(min_length=20, max_length=2048)


class JoinGatheringRequest(APIModel):
    role: str | None = Field(default=None, max_length=64)
    joined_via: str = Field(default="open", max_length=32)


class ConfirmGatheringRequest(APIModel):
    confirmed: bool = True


class LeaveGatheringRequest(APIModel):
    reason: str | None = Field(default=None, max_length=300)


class RescheduleRequest(APIModel):
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> RescheduleRequest:
        if ensure_utc(self.end_at) <= ensure_utc(self.start_at):
            raise ValueError("结束时间必须晚于开始时间")
        return self


class RescheduleVoteRequest(APIModel):
    accepted: bool


class RescheduleProposalView(APIModel):
    proposal_id: str
    gathering_id: str
    status: str
    start_at: datetime
    end_at: datetime
    feasible_count: int
    accepted_count: int
    required_count: int
    my_vote: str | None = None
    expires_at: datetime | None = None
    decided_at: datetime | None = None


class CompleteRequest(APIModel):
    completed: bool


class RecurRequest(APIModel):
    keep_user_ids: list[str] | None = Field(default=None, max_length=20)


class ReportRequest(APIModel):
    reported_user_id: str | None = None
    reason: str = Field(min_length=5, max_length=1000)
    block: bool = True


class ReportResolution(APIModel):
    valid: bool
