from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from onemore.core.schemas import APIModel
from onemore.core.time import ensure_utc


class IntentCapability(APIModel):
    key: str = Field(min_length=1, max_length=64)
    source: Literal["verified", "self_reported", "ai_inferred"]


class IntentWindow(APIModel):
    start_at: datetime
    end_at: datetime
    stability: float = Field(default=1.0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_window(self) -> IntentWindow:
        if ensure_utc(self.end_at) <= ensure_utc(self.start_at):
            raise ValueError("结束时间必须晚于开始时间")
        return self


class IntentCardView(APIModel):
    id: str
    status: str
    gathering_type: str
    mode: Literal["similar", "complementary"]
    goal: str
    mood_note: str | None = None
    capabilities: list[IntentCapability]
    required_roles: list[str]
    intensity: str
    available_windows: list[IntentWindow]
    campus: str | None
    min_size: int
    target_size: int
    social_mode: Literal["after_confirmed", "after_full"]
    same_gender_only: bool
    competition_id: str | None
    expires_at: datetime
    field_sources: dict[str, str]
    clarification_rounds: int


class IntentCompileRequest(APIModel):
    text: str = Field(min_length=1, max_length=1000)
    mood_note: str | None = Field(default=None, max_length=60)
    competition_id: str | None = None
    clarification_round: int = Field(default=0, ge=0, le=2)
    answers: dict[str, str] = Field(default_factory=dict)


class IntentClarificationQuestion(APIModel):
    key: Literal["availability", "required_roles"]
    prompt: str
    input_type: Literal["time_window", "role_list"]


class IntentCompileResult(APIModel):
    card: IntentCardView
    needs_clarification: bool
    questions: list[IntentClarificationQuestion]
    max_rounds: int = 2


class IntentCardPatch(APIModel):
    gathering_type: str | None = Field(default=None, max_length=64)
    goal: str | None = Field(default=None, min_length=1, max_length=500)
    mood_note: str | None = Field(default=None, max_length=60)
    capabilities: list[IntentCapability] | None = Field(default=None, max_length=40)
    required_roles: list[str] | None = Field(default=None, max_length=20)
    intensity: str | None = Field(default=None, max_length=64)
    available_windows: list[IntentWindow] | None = Field(default=None, max_length=30)
    campus: str | None = Field(default=None, max_length=64)
    min_size: int | None = Field(default=None, ge=2, le=20)
    target_size: int | None = Field(default=None, ge=2, le=20)
    social_mode: Literal["after_confirmed", "after_full"] | None = None
    same_gender_only: bool | None = None
    expires_at: datetime | None = None


class IntentPublishRequest(APIModel):
    card_id: str


class IntentPublishResult(APIModel):
    intent_id: str
    gathering_id: str
    status: str
    expires_at: datetime
