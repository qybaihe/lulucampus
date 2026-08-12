from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from onemore.core.schemas import APIModel


class LoginSessionCreate(APIModel):
    device_install_id: str | None = Field(default=None, max_length=128)
    resume_user_id: str | None = None


class PhoneRegister(APIModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    password: str = Field(min_length=6, max_length=64)
    display_name: str | None = Field(default=None, min_length=1, max_length=80)


class PhoneLogin(APIModel):
    phone: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=1, max_length=64)


class PhoneAuthView(APIModel):
    access_token: str
    user_id: str
    display_name: str | None = None
    is_new_user: bool = False


class LoginSessionView(APIModel):
    id: str
    user_id: str
    status: str
    qr_image_data_url: str | None
    deep_link: str | None
    expires_at: datetime
    access_token: str | None = None
    redemption_token: str | None = None
    error_category: str | None = None


class LoginRedemption(APIModel):
    redemption_token: str = Field(min_length=32, max_length=512)


class LoginRedemptionView(APIModel):
    access_token: str


class GrantChange(APIModel):
    scope: Literal["timetable", "curriculum", "enrollment", "agent_booking"]
    granted: bool


class GrantView(APIModel):
    scope: str
    granted: bool
    granted_at: datetime | None
    revoked_at: datetime | None


class SessionHealthView(APIModel):
    subsystem: str
    healthy: bool
    last_checked_at: datetime | None
    error_category: str | None


class IdentityFactsView(APIModel):
    user_id: str
    display_name: str | None
    verified: bool
    college: str | None
    major: str | None
    grade_year: int | None
    campus: str | None
    gender_code: str | None
    social_enabled: bool
    course_matching_enabled: bool
    identity_disclosure: str
    same_gender_only: bool
    minimum_group_size: int
    scene_sensitive_policy: Literal["mute_onsite"] = "mute_onsite"
    grants: list[GrantView]
    session_health: list[SessionHealthView]


class SocialPreferenceChange(APIModel):
    social_enabled: bool | None = None
    course_matching_enabled: bool | None = None
    identity_disclosure: Literal["after_confirmed", "after_full"] | None = None
    same_gender_only: bool | None = None
    minimum_group_size: int | None = Field(default=None, ge=2, le=20)


class SocialPreferenceView(APIModel):
    social_enabled: bool
    course_matching_enabled: bool
    identity_disclosure: Literal["after_confirmed", "after_full"]
    same_gender_only: bool
    minimum_group_size: int
    scene_sensitive_policy: Literal["mute_onsite"] = "mute_onsite"


class MatchingPreferenceChange(APIModel):
    interaction_style: Literal["quiet", "balanced", "talkative"] | None = None
    sport_level: Literal["beginner", "casual", "intermediate", "advanced"] | None = None
    study_intensity: Literal["light", "balanced", "focused"] | None = None


class MatchingPreferenceView(APIModel):
    interaction_style: Literal["quiet", "balanced", "talkative"] = "balanced"
    sport_level: Literal["beginner", "casual", "intermediate", "advanced"] = "casual"
    study_intensity: Literal["light", "balanced", "focused"] = "balanced"
