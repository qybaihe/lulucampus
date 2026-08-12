from __future__ import annotations

from typing import Literal

from pydantic import Field

from onemore.core.schemas import APIModel


class CapabilityView(APIModel):
    key: str
    label: str
    source: Literal["verified", "self_reported", "taste"]
    weight: float
    hidden: bool = False


class CapabilityOptionView(APIModel):
    key: str
    label: str


class ProfileView(APIModel):
    user_id: str
    init_status: str
    init_progress: dict
    identity: dict
    capabilities: list[CapabilityView]
    available_capabilities: list[CapabilityOptionView] = Field(default_factory=list)
    interest_domains: list[str]
    cross_major_score: float
    trust_progress: dict
    taste_profile: dict | None = None


class SelfReportedTagsPatch(APIModel):
    tags: list[str] = Field(max_length=30)
    hidden_verified_tags: list[str] = Field(default_factory=list, max_length=30)


class ProfileInitRequest(APIModel):
    force: bool = False
