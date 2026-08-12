from __future__ import annotations

from typing import Literal

from onemore.core.schemas import APIModel


class AccountDeleteRequest(APIModel):
    confirmation: Literal["DELETE"]
