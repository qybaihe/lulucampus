from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from onemore.core.auth import current_user, require_admin
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.trust import service
from onemore.modules.trust.schemas import (
    AppealCreate,
    AppealResolution,
    AppealView,
    TrustProgressView,
)

router = APIRouter(tags=["trust"])
internal_router = APIRouter(prefix="/internal", tags=["trust-internal"])


@router.get("/trust/me", response_model=APIResponse[TrustProgressView])
def my_trust_progress(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[TrustProgressView]:
    return APIResponse(data=TrustProgressView.model_validate(service.get_progress(db, user.id)))


@router.post(
    "/trust/appeal",
    response_model=APIResponse[AppealView],
    status_code=status.HTTP_201_CREATED,
)
def submit_appeal(
    body: AppealCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[AppealView]:
    appeal = service.create_appeal(db, user.id, body.reason)
    return APIResponse(data=AppealView.model_validate(appeal))


@router.get("/trust/appeals", response_model=APIResponse[list[AppealView]])
def my_appeals(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[list[AppealView]]:
    return APIResponse(
        data=[AppealView.model_validate(item) for item in service.list_appeals(db, user.id)]
    )


@router.get("/trust/appeals/{appeal_id}", response_model=APIResponse[AppealView])
def appeal_result(
    appeal_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[AppealView]:
    return APIResponse(data=AppealView.model_validate(service.get_appeal(db, appeal_id, user.id)))


@internal_router.post(
    "/trust/appeals/{appeal_id}/resolve",
    response_model=APIResponse[AppealView],
    dependencies=[Depends(require_admin)],
)
def resolve_appeal(
    appeal_id: str,
    body: AppealResolution,
    db: Session = Depends(get_db),
) -> APIResponse[AppealView]:
    return APIResponse(
        data=AppealView.model_validate(
            service.resolve_appeal(db, appeal_id, body.status, body.result)
        )
    )
