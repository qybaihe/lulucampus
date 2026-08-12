from __future__ import annotations

from typing import Literal

from pydantic import Field

from onemore.core.schemas import APIModel


class ImageAssetView(APIModel):
    media_id: str
    url: str
    content_type: Literal["image/jpeg", "image/png", "image/heic", "image/heif"]
    byte_count: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)
    width: int | None = Field(default=None, gt=0, le=20000)
    height: int | None = Field(default=None, gt=0, le=20000)
