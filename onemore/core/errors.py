from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} 不存在",
            status_code=404,
            details={"id": resource_id},
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "当前账号没有执行此操作的权限") -> None:
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code=code, message=message, status_code=409, details=details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "请先登录") -> None:
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)
