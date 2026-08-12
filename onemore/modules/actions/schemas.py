from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from onemore.core.schemas import APIModel
from onemore.hermes.schemas import ActionName


class ActionPreviewRequest(APIModel):
    action: ActionName
    params: dict[str, Any]
    gathering_id: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)
    confirm: bool = False


class ActionExecuteRequest(APIModel):
    action_id: str
    params: dict[str, Any] | None = None
    confirm: bool = False


class ActionAuthorizationRequest(APIModel):
    authorized: bool
    snapshot_hash: str = Field(min_length=64, max_length=64)


class ActionModificationRequest(APIModel):
    snapshot_hash: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=5, max_length=500)
    proposed_params: dict[str, Any] = Field(default_factory=dict)


class ActionModificationView(APIModel):
    reason: str
    proposed_params: dict[str, Any]
    status: str
    created_at: datetime


class ActionAuthorizationView(APIModel):
    required_count: int
    authorized_count: int
    actor_decision: str
    all_authorized: bool


class CampusActionView(APIModel):
    id: str
    user_id: str
    gathering_id: str | None
    action_name: str
    status: str
    params: dict[str, Any]
    preview_snapshot: dict[str, Any]
    snapshot_hash: str
    authorization: ActionAuthorizationView
    modification: ActionModificationView | None = None
    execution_result: dict[str, Any] | None
    error_category: str | None
