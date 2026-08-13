from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from onemore.core.schemas import APIModel


class HermesAskRequest(APIModel):
    text: str = Field(min_length=1, max_length=1000)
    context: dict[str, Any] = Field(default_factory=dict)


class HermesToolTrace(APIModel):
    name: str
    ok: bool = True
    summary: str | None = None
    card_type: str | None = None


class HermesAskResult(APIModel):
    kind: str
    action: str | None = None
    card_type: str
    data: Any
    requires_preview: bool = False
    tool_trace: list[HermesToolTrace] = Field(default_factory=list)


class HermesPeerStartRequest(APIModel):
    peer_user_id: str = Field(min_length=8, max_length=36)
    reason: str = Field(default="", max_length=200)
    overlap: str = Field(default="taste", max_length=16)


class HermesPeerChatResult(APIModel):
    channel_id: str
    gathering_id: str


class SceneTriggerIgnore(APIModel):
    ignored: bool = True


class CampusEventCreateRequest(APIModel):
    """用户发布校园活动（T4 门槛）。匿名展示，不携带发布者身份。"""

    title: str = Field(min_length=2, max_length=60)
    type: str = Field(min_length=1, max_length=16)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=500)
    official_url: str | None = Field(default=None, max_length=500)


class PublicEventView(APIModel):
    """Stable RFC 3339 contract for public campus events."""

    id: str
    type: str
    title: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = None
    official_url: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    registration_mode: str = "official_link_only"
