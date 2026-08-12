from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from onemore.core.auth import current_user
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.identity import account
from onemore.modules.identity.account_schemas import AccountDeleteRequest

router = APIRouter(tags=["account"])


@router.get("/me/blocks", response_model=APIResponse[list[dict]])
def my_blocks(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[list[dict]]:
    return APIResponse(data=account.list_blocks(db, user.id))


@router.post(
    "/me/blocks/{blocked_user_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_201_CREATED,
)
def add_block(
    blocked_user_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    item = account.block_user(db, user.id, blocked_user_id)
    return APIResponse(data={"blocked_user_id": item.blocked_id, "created_at": item.created_at})


@router.delete("/me/blocks/{blocked_user_id}", response_model=APIResponse[dict])
def remove_block(
    blocked_user_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    account.unblock_user(db, user.id, blocked_user_id)
    return APIResponse(data={"blocked_user_id": blocked_user_id, "blocked": False})


@router.get("/me/data-export", response_model=APIResponse[dict])
def export_my_data(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[dict]:
    return APIResponse(data=account.export_user_data(db, user.id))


@router.delete("/me/account", response_model=APIResponse[dict])
def delete_my_account(
    body: AccountDeleteRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    account.deactivate_account(db, user.id)
    return APIResponse(data={"status": "deleted"})
