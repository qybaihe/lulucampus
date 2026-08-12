from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("*", mode="after", check_fields=False)
    @classmethod
    def normalize_naive_datetimes(cls, value: Any) -> Any:
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class APIResponse[T](BaseModel):
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)


class AcceptedResponse(APIModel):
    id: str
    status: str
    accepted_at: datetime


class PageMeta(APIModel):
    next_cursor: str | None = None
    has_more: bool = False
