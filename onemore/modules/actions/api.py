from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from onemore.core.auth import current_user, require_admin
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.actions import service
from onemore.modules.actions.schemas import (
    ActionAuthorizationRequest,
    ActionExecuteRequest,
    ActionModificationRequest,
    ActionPreviewRequest,
    CampusActionView,
)

router = APIRouter(tags=["actions"])


def _view(db: Session, action, actor_id: str) -> CampusActionView:
    value = {
        key: getattr(action, key)
        for key in CampusActionView.model_fields
        if key not in {"authorization", "modification"}
    }
    value["authorization"] = service.authorization_view(db, action, actor_id)
    value["modification"] = service.modification_view(db, action)
    return CampusActionView.model_validate(value)


@router.post("/actions/preview", response_model=APIResponse[CampusActionView])
def preview_action(
    body: ActionPreviewRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[CampusActionView]:
    action = service.preview(
        db,
        user,
        action=body.action,
        params=body.params,
        gathering_id=body.gathering_id,
        idempotency_key=body.idempotency_key,
        client_confirm=body.confirm,
    )
    return APIResponse(data=_view(db, action, user.id))


@router.post("/actions/execute", response_model=APIResponse[CampusActionView])
def execute_action(
    body: ActionExecuteRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[CampusActionView]:
    action = service.execute(
        db,
        user,
        action_id=body.action_id,
        params=body.params,
        client_confirm=body.confirm,
    )
    return APIResponse(data=_view(db, action, user.id))


@router.get("/actions/{action_id}", response_model=APIResponse[CampusActionView])
def get_action(
    action_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[CampusActionView]:
    action = service.get_for_member(db, action_id, user.id)
    return APIResponse(data=_view(db, action, user.id))


@router.post(
    "/actions/{action_id}/authorization",
    response_model=APIResponse[CampusActionView],
)
def authorize_action(
    action_id: str,
    body: ActionAuthorizationRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[CampusActionView]:
    action = service.authorize(
        db,
        action_id,
        user.id,
        authorized=body.authorized,
        snapshot_hash=body.snapshot_hash,
    )
    return APIResponse(data=_view(db, action, user.id))


@router.post(
    "/actions/{action_id}/propose-modification",
    response_model=APIResponse[CampusActionView],
)
def propose_action_modification(
    action_id: str,
    body: ActionModificationRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[CampusActionView]:
    action = service.propose_modification(
        db,
        action_id,
        user.id,
        snapshot_hash=body.snapshot_hash,
        reason=body.reason,
        proposed_params=body.proposed_params,
    )
    return APIResponse(data=_view(db, action, user.id))


@router.post(
    "/internal/actions/{action_id}/rollback",
    response_model=APIResponse[CampusActionView],
    dependencies=[Depends(require_admin)],
)
def rollback_action(action_id: str, db: Session = Depends(get_db)) -> APIResponse[CampusActionView]:
    action = service.rollback(db, action_id)
    return APIResponse(data=_view(db, action, action.user_id))
