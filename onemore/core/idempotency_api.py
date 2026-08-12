from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.auth import current_user
from onemore.core.database import get_db
from onemore.core.errors import NotFoundError
from onemore.core.schemas import APIResponse
from onemore.db.models import IdempotencyRecord, User

router = APIRouter(tags=["idempotency"])


@router.get("/idempotency/operations/{key}", response_model=APIResponse[dict])
def idempotency_operation_status(
    key: str,
    method: str = Query(pattern="^(POST|PATCH|DELETE)$"),
    path: str = Query(min_length=1, max_length=512),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    record = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user.id,
            IdempotencyRecord.method == method,
            IdempotencyRecord.path == path,
            IdempotencyRecord.idempotency_key == key,
        )
    )
    if record is None:
        raise NotFoundError("幂等操作", key)
    if record.response_status > 0:
        status = "completed"
    elif record.response_status == 0:
        status = "in_progress"
    else:
        status = "unknown_after_interruption"
    return APIResponse(
        data={
            "idempotency_key": key,
            "method": method,
            "path": path,
            "status": status,
            "response_status": record.response_status if record.response_status > 0 else None,
            "created_at": record.created_at,
            "expires_at": record.expires_at,
            "safe_to_repeat": False if status != "completed" else None,
        }
    )
