from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from onemore.core.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class LoginStatus(enum.StrEnum):
    PENDING = "PENDING"
    WAITING_SCAN = "WAITING_SCAN"
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class GrantScope(enum.StrEnum):
    TIMETABLE = "timetable"
    CURRICULUM = "curriculum"
    ENROLLMENT = "enrollment"
    AGENT_BOOKING = "agent_booking"


class ProfileInitStatus(enum.StrEnum):
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"


class IntentStatus(enum.StrEnum):
    DRAFT = "Draft"
    NEEDS_CLARIFICATION = "NeedsClarification"
    POOLING = "Pooling"
    WITHDRAWN = "Withdrawn"
    EXPIRED = "Expired"
    MATCHED = "Matched"


class GatheringStatus(enum.StrEnum):
    DRAFT = "Draft"
    POOLING = "Pooling"
    TENTATIVE = "Tentative"
    CONFIRMED = "Confirmed"
    PREVIEWED = "Previewed"
    EXECUTED = "Executed"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    RECURRENCE_PENDING = "Recurred"
    ARCHIVED = "Archived"
    DISSOLVED = "Dissolved"


class ConfirmationStatus(enum.StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    TIMED_OUT = "timed_out"


class TrustLevel(enum.StrEnum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


class ChannelStatus(enum.StrEnum):
    OPEN = "open"
    ARCHIVED = "archived"
    CLOSED = "closed"


class RelationStatus(enum.StrEnum):
    ACTIVE = "active"
    DISSOLVED = "dissolved"


class ActionStatus(enum.StrEnum):
    PREVIEWED = "previewed"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INVALIDATED = "invalidated"
    ROLLED_BACK = "rolled_back"


class CompetitionStatus(enum.StrEnum):
    ACTIONABLE = "actionable"
    EXPIRED = "expired"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    netid_hash: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    college: Mapped[str | None] = mapped_column(String(128), nullable=True)
    major: Mapped[str | None] = mapped_column(String(128), nullable=True)
    grade_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    campus: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gender_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    social_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    course_matching_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    calendar_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_preferences: Mapped[dict[str, bool]] = mapped_column(
        JSON,
        default=lambda: {
            "gathering_updates": True,
            "action_updates": True,
            "chat_messages": True,
            "trust_updates": True,
            "competition_deadlines": True,
            "schedule_reminders": True,
        },
    )
    identity_disclosure: Mapped[str] = mapped_column(String(32), default="after_confirmed")
    same_gender_only: Mapped[bool] = mapped_column(Boolean, default=False)
    minimum_group_size: Mapped[int] = mapped_column(Integer, default=3)
    matching_preferences: Mapped[dict[str, str]] = mapped_column(
        JSON,
        default=lambda: {
            "interaction_style": "balanced",
            "sport_level": "casual",
            "study_intensity": "balanced",
        },
    )
    account_status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthorizationGrant(TimestampMixin, Base):
    __tablename__ = "authorization_grants"
    __table_args__ = (UniqueConstraint("user_id", "scope"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope: Mapped[str] = mapped_column(String(32))
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LoginSession(TimestampMixin, Base):
    __tablename__ = "login_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=LoginStatus.PENDING.value)
    qr_image_data_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    deep_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    error_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    redemption_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_install_id_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redemption_operation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    redemption_response_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)


class SessionHealth(TimestampMixin, Base):
    __tablename__ = "session_health"
    __table_args__ = (UniqueConstraint("user_id", "subsystem"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subsystem: Mapped[str] = mapped_column(String(32))
    healthy: Mapped[bool] = mapped_column(Boolean, default=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(32), nullable=True)


class CapabilityTag(Base):
    __tablename__ = "capability_tags"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(64))
    domain: Mapped[str] = mapped_column(String(64), index=True)


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    domain: Mapped[str] = mapped_column(String(64), index=True)
    capability_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    course_type: Mapped[str] = mapped_column(String(32), default="elective")


class Enrollment(TimestampMixin, Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", "class_code", "term"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    class_code: Mapped[str] = mapped_column(String(64), index=True)
    term: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default="current")
    course_type: Mapped[str] = mapped_column(String(32), default="elective")
    meeting_windows: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class TasteImportSession(TimestampMixin, Base):
    __tablename__ = "taste_import_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(16), default="douyin")
    status: Mapped[str] = mapped_column(String(32), default="PREPARING_QR", index=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_items: Mapped[int] = mapped_column(Integer, default=0)
    qr_image_data_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_version: Mapped[int] = mapped_column(Integer, default=0)
    qr_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    authenticated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    progress: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    collection_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    candidate_tags: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    answers: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    analysis_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TasteProfile(Base):
    __tablename__ = "taste_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(16), default="douyin")
    source_import_id: Mapped[str | None] = mapped_column(
        ForeignKey("taste_import_sessions.id", ondelete="SET NULL"), nullable=True
    )
    primary_tag: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    secondary_tags: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    interest_domains: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    dimensions: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sample_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String(32), default="taste-v1")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    init_status: Mapped[str] = mapped_column(
        String(32), default=ProfileInitStatus.NOT_STARTED.value
    )
    init_progress: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    verified_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    self_reported_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    hidden_verified_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    capability_vector: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    interest_domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    cross_major_score: Mapped[float] = mapped_column(Float, default=0.0)


class TimeWindow(TimestampMixin, Base):
    __tablename__ = "time_windows"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="positive_window"),
        Index("ix_time_windows_user_range", "user_id", "start_at", "end_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    campus: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    stability: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(32), default="timetable")


class Assignment(TimestampMixin, Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), default="unfinished")
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)


class IntentCard(TimestampMixin, Base):
    __tablename__ = "intent_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=IntentStatus.DRAFT.value, index=True)
    gathering_type: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="similar")
    goal: Mapped[str] = mapped_column(String(500))
    # Anonymous one-line vibe written by the initiator; carries personality
    # without identity, so it stays visible during silent pooling.
    mood_note: Mapped[str | None] = mapped_column(String(120), nullable=True)
    capabilities: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    required_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    intensity: Mapped[str] = mapped_column(String(64), default="balanced")
    available_windows: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    campus: Mapped[str | None] = mapped_column(String(64), nullable=True)
    min_size: Mapped[int] = mapped_column(Integer, default=3)
    target_size: Mapped[int] = mapped_column(Integer, default=4)
    social_mode: Mapped[str] = mapped_column(String(64), default="after_full")
    same_gender_only: Mapped[bool] = mapped_column(Boolean, default=False)
    competition_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    clarification_rounds: Mapped[int] = mapped_column(Integer, default=0)
    clarification_questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    field_sources: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    edited_fields: Mapped[list[str]] = mapped_column(JSON, default=list)


class Gathering(TimestampMixin, Base):
    __tablename__ = "gatherings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_intent_id: Mapped[str | None] = mapped_column(
        ForeignKey("intent_cards.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    gathering_type: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="similar")
    title: Mapped[str] = mapped_column(String(256))
    goal: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), default=GatheringStatus.DRAFT.value, index=True)
    min_size: Mapped[int] = mapped_column(Integer, default=3)
    target_size: Mapped[int] = mapped_column(Integer, default=4)
    required_trust_level: Mapped[str] = mapped_column(String(8), default=TrustLevel.T1.value)
    campus: Mapped[str | None] = mapped_column(String(64), nullable=True)
    same_gender_only: Mapped[bool] = mapped_column(Boolean, default=False)
    identity_disclosure: Mapped[str] = mapped_column(String(32), default="after_full")
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    required_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    official_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmation_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GatheringMember(TimestampMixin, Base):
    __tablename__ = "gathering_members"
    __table_args__ = (UniqueConstraint("gathering_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    gathering_id: Mapped[str] = mapped_column(
        ForeignKey("gatherings.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confirmation_status: Mapped[str] = mapped_column(
        String(32), default=ConfirmationStatus.PENDING.value
    )
    joined_via: Mapped[str] = mapped_column(String(32), default="intent")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GatheringTransition(Base):
    __tablename__ = "gathering_transitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    gathering_id: Mapped[str] = mapped_column(
        ForeignKey("gatherings.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    event: Mapped[str] = mapped_column(String(64))
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RescheduleProposal(TimestampMixin, Base):
    __tablename__ = "reschedule_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    gathering_id: Mapped[str] = mapped_column(
        ForeignKey("gatherings.id", ondelete="CASCADE"), index=True
    )
    proposed_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    feasible_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="open")
    eligible_user_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RescheduleVote(Base):
    __tablename__ = "reschedule_votes"
    __table_args__ = (UniqueConstraint("proposal_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("reschedule_proposals.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    accepted: Mapped[bool] = mapped_column(Boolean)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CampusAction(TimestampMixin, Base):
    __tablename__ = "campus_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    gathering_id: Mapped[str | None] = mapped_column(
        ForeignKey("gatherings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action_name: Mapped[str] = mapped_column(String(64))
    commit_action_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    preview_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default=ActionStatus.PREVIEWED.value)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ActionAuthorization(Base):
    __tablename__ = "action_authorizations"
    __table_args__ = (UniqueConstraint("action_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    action_id: Mapped[str] = mapped_column(
        ForeignKey("campus_actions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(16), default="pending")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActionModification(TimestampMixin, Base):
    __tablename__ = "action_modifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    action_id: Mapped[str] = mapped_column(
        ForeignKey("campus_actions.id", ondelete="CASCADE"), index=True
    )
    requester_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    proposed_params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="requested")


class TrustProfile(TimestampMixin, Base):
    __tablename__ = "trust_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    level: Mapped[str] = mapped_column(String(8), default=TrustLevel.T0.value)
    completed_gatherings: Mapped[int] = mapped_column(Integer, default=0)
    initiated_gatherings: Mapped[int] = mapped_column(Integer, default=0)
    recurrences: Mapped[int] = mapped_column(Integer, default=0)
    on_time_confirm_rate: Mapped[float] = mapped_column(Float, default=1.0)
    late_exit_rate: Mapped[float] = mapped_column(Float, default=0.0)
    no_show_count_30d: Mapped[int] = mapped_column(Integer, default=0)
    valid_report_count: Mapped[int] = mapped_column(Integer, default=0)
    observation_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    previous_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    organizer_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class OfficialGatheringTemplate(TimestampMixin, Base):
    __tablename__ = "official_gathering_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(256))
    goal: Mapped[str] = mapped_column(String(500))
    gathering_type: Mapped[str] = mapped_column(String(64), index=True)
    min_size: Mapped[int] = mapped_column(Integer, default=3)
    target_size: Mapped[int] = mapped_column(Integer, default=4)
    campus: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str] = mapped_column(String(256))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=120)
    required_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    recurrence_rule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class OrganizerAttendance(Base):
    __tablename__ = "organizer_attendance"
    __table_args__ = (UniqueConstraint("gathering_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    gathering_id: Mapped[str] = mapped_column(
        ForeignKey("gatherings.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TrustEvent(Base):
    __tablename__ = "trust_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TrustAppeal(TimestampMixin, Base):
    __tablename__ = "trust_appeals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="submitted")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Relation(TimestampMixin, Base):
    __tablename__ = "relations"
    __table_args__ = (
        UniqueConstraint("participant_a_id", "participant_b_id"),
        CheckConstraint("participant_a_id < participant_b_id", name="sorted_participants"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    participant_a_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    participant_b_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_from_gathering_id: Mapped[str] = mapped_column(ForeignKey("gatherings.id"))
    status: Mapped[str] = mapped_column(String(32), default=RelationStatus.ACTIVE.value)
    dissolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dissolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SharedExperience(Base):
    __tablename__ = "shared_experiences"
    __table_args__ = (UniqueConstraint("relation_id", "gathering_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    relation_id: Mapped[str] = mapped_column(
        ForeignKey("relations.id", ondelete="CASCADE"), index=True
    )
    gathering_id: Mapped[str] = mapped_column(ForeignKey("gatherings.id"), index=True)
    participants: Mapped[list[str]] = mapped_column(JSON)
    gathering_type: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(32))
    common_grounds: Mapped[list[str]] = mapped_column(JSON, default=list)


class Channel(TimestampMixin, Base):
    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    gathering_id: Mapped[str | None] = mapped_column(
        ForeignKey("gatherings.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    relation_id: Mapped[str | None] = mapped_column(
        ForeignKey("relations.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    status: Mapped[str] = mapped_column(String(32), default=ChannelStatus.OPEN.value)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChannelParticipant(Base):
    __tablename__ = "channel_participants"
    __table_args__ = (UniqueConstraint("channel_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_channel_sent", "channel_id", "sent_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[str] = mapped_column(String(36), index=True)
    sender_type: Mapped[str] = mapped_column(String(16), default="human")
    content_type: Mapped[str] = mapped_column(String(16), default="text")
    content: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(64))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(Text)
    byte_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MediaChannelGrant(Base):
    __tablename__ = "media_channel_grants"
    __table_args__ = (UniqueConstraint("media_id", "channel_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    media_id: Mapped[str] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"), index=True
    )
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SharedGoal(TimestampMixin, Base):
    __tablename__ = "shared_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    relation_id: Mapped[str] = mapped_column(ForeignKey("relations.id"), index=True)
    definition: Mapped[str] = mapped_column(String(500))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    target_value: Mapped[float] = mapped_column(Float)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="active")
    milestones: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    next_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_broadcast: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_progress_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SharedGoalMemberProgress(TimestampMixin, Base):
    __tablename__ = "shared_goal_member_progress"
    __table_args__ = (UniqueConstraint("goal_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    goal_id: Mapped[str] = mapped_column(
        ForeignKey("shared_goals.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_progress_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GatheringRecurrenceDecision(TimestampMixin, Base):
    __tablename__ = "gathering_recurrence_decisions"
    __table_args__ = (UniqueConstraint("gathering_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    gathering_id: Mapped[str] = mapped_column(
        ForeignKey("gatherings.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    decision: Mapped[str] = mapped_column(String(32))
    kept_user_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    clone_gathering_id: Mapped[str | None] = mapped_column(
        ForeignKey("gatherings.id", ondelete="SET NULL"), nullable=True
    )


class CompetitionEvent(TimestampMixin, Base):
    __tablename__ = "competition_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    external_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    verification_status: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default=CompetitionStatus.ACTIONABLE.value)
    registration_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    submission_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String(32), default="online")
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    rewards: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_url: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    tracks: Mapped[list[str]] = mapped_column(JSON, default=list)
    participation_mode: Mapped[str] = mapped_column(String(32), default="team")
    registration_mode: Mapped[str] = mapped_column(String(32), default="direct")
    registration_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    fee_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_tier: Mapped[str] = mapped_column(String(1), default="B", index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_version: Mapped[str] = mapped_column(String(64))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CompetitionSkill(Base):
    __tablename__ = "competition_skills"
    __table_args__ = (UniqueConstraint("competition_id", "capability_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competition_events.id", ondelete="CASCADE"), index=True
    )
    capability_key: Mapped[str] = mapped_column(ForeignKey("capability_tags.key"))
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class CompetitionConstraint(Base):
    __tablename__ = "competition_constraints"

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competition_events.id", ondelete="CASCADE"), primary_key=True
    )
    team_size_min: Mapped[int] = mapped_column(Integer, default=2)
    team_size_max: Mapped[int] = mapped_column(Integer, default=5)
    eligibility: Mapped[list[str]] = mapped_column(JSON, default=list)


class ExternalEvent(TimestampMixin, Base):
    __tablename__ = "external_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source: Mapped[str] = mapped_column(String(32), index=True)
    external_key: Mapped[str] = mapped_column(String(128), unique=True)
    title: Mapped[str] = mapped_column(String(256))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    official_url: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "type", "dedupe_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PushDevice(TimestampMixin, Base):
    __tablename__ = "push_devices"
    __table_args__ = (
        UniqueConstraint("user_id", "token_hash"),
        Index("ux_push_devices_token_hash", "token_hash", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128))
    token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str] = mapped_column(String(16), default="ios")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PushDelivery(TimestampMixin, Base):
    __tablename__ = "push_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[str] = mapped_column(
        ForeignKey("push_devices.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    provider_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("user_id", "method", "path", "idempotency_key"),
        Index("ix_idempotency_records_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(512))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[str] = mapped_column(Text)
    response_content_type: Mapped[str] = mapped_column(String(128), default="application/json")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    blocker_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    blocked_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    reported_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    gathering_id: Mapped[str] = mapped_column(ForeignKey("gatherings.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="submitted")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SceneTrigger(TimestampMixin, Base):
    __tablename__ = "scene_triggers"
    __table_args__ = (UniqueConstraint("user_id", "scene_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scene_key: Mapped[str] = mapped_column(String(64))
    last_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ignored_count: Mapped[int] = mapped_column(Integer, default=0)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)


class CastDriverEvent(Base):
    """Audit log for the demo-cast live driver. Not a product surface."""

    __tablename__ = "cast_driver_events"
    __table_args__ = (Index("ix_cast_driver_events_user_occurred", "user_id", "occurred_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
