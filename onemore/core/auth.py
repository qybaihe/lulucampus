from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.database import get_db
from onemore.core.errors import ForbiddenError, UnauthorizedError
from onemore.db.models import User


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_access_token(user_id: str) -> str:
    settings = get_settings()
    payload = json.dumps(
        {
            "sub": user_id,
            "exp": int(time.time()) + settings.access_token_ttl_seconds,
            "v": 1,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = _b64encode(payload)
    signature = hmac.new(
        settings.auth_signing_key.encode(), encoded.encode(), hashlib.sha256
    ).digest()
    return f"om1.{encoded}.{_b64encode(signature)}"


def user_id_from_token(token: str) -> str | None:
    settings = get_settings()
    if settings.dev_auth_enabled and token.startswith("dev:"):
        return token[4:] or None
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "om1":
        return None
    expected = hmac.new(
        settings.auth_signing_key.encode(), parts[1].encode(), hashlib.sha256
    ).digest()
    try:
        signature = _b64decode(parts[2])
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_b64decode(parts[1]))
        if payload.get("v") != 1 or int(payload.get("exp", 0)) <= int(time.time()):
            return None
        user_id = payload.get("sub")
        return user_id if isinstance(user_id, str) and user_id else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _extract_user_id(authorization: str | None, x_user_id: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        return user_id_from_token(token)
    if get_settings().dev_auth_enabled and x_user_id:
        return x_user_id.strip()
    return None


def user_id_from_credentials(
    authorization: str | None, x_user_id: str | None
) -> str | None:
    """Authenticate HTTP or WebSocket headers without placing tokens in URLs."""

    return _extract_user_id(authorization, x_user_id)


def current_principal(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> Principal:
    user_id = _extract_user_id(authorization, x_user_id)
    if not user_id:
        raise UnauthorizedError()
    return Principal(user_id=user_id)


def current_user(
    principal: Principal = __import__("fastapi").Depends(current_principal),
    db: Session = __import__("fastapi").Depends(get_db),
) -> User:
    user = db.scalar(select(User).where(User.id == principal.user_id))
    if user is None or user.account_status != "active":
        raise UnauthorizedError("登录身份不存在或已失效")
    return user


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != get_settings().admin_token:
        raise ForbiddenError("管理员令牌无效")
