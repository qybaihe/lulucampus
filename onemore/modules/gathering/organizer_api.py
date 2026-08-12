from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from onemore.core.auth import current_user, require_admin
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.gathering import organizer
from onemore.modules.gathering.organizer_schemas import (
    OfficialGatheringCreate,
    OfficialGatheringCreatedView,
    OfficialGatheringSummaryView,
    OfficialTemplateCopy,
    OfficialTemplateCreate,
    OfficialTemplatePatch,
    OfficialTemplateView,
    OrganizerAttendanceView,
    OrganizerDashboardView,
    OrganizerGatheringStatusView,
    OrganizerVerification,
    TemplateInstantiate,
)

router = APIRouter(prefix="/organizer", tags=["organizer"])
internal_router = APIRouter(prefix="/internal", tags=["organizer-internal"])


@router.post(
    "/gatherings",
    response_model=APIResponse[OfficialGatheringCreatedView],
    status_code=status.HTTP_201_CREATED,
)
def create_official_gathering(
    body: OfficialGatheringCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OfficialGatheringCreatedView]:
    item = organizer.create_official(db, user.id, body)
    return APIResponse(
        data=OfficialGatheringCreatedView(id=item.id, status=item.status)
    )


@router.get(
    "/gatherings",
    response_model=APIResponse[list[OfficialGatheringSummaryView]],
)
def list_official_gatherings(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[list[OfficialGatheringSummaryView]]:
    return APIResponse(
        data=[
            OfficialGatheringSummaryView.model_validate(item)
            for item in organizer.list_official(db, user.id)
        ]
    )


@router.get(
    "/gatherings/{gathering_id}/dashboard",
    response_model=APIResponse[OrganizerDashboardView],
)
def official_dashboard(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OrganizerDashboardView]:
    return APIResponse(
        data=OrganizerDashboardView.model_validate(
            organizer.dashboard(db, gathering_id, user.id)
        )
    )


@router.post(
    "/gatherings/{gathering_id}/finalize",
    response_model=APIResponse[OrganizerGatheringStatusView],
)
def finalize_official_gathering(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OrganizerGatheringStatusView]:
    item = organizer.finalize_official(db, gathering_id, user.id)
    return APIResponse(
        data=OrganizerGatheringStatusView(id=item.id, status=item.status)
    )


@router.post(
    "/gatherings/{gathering_id}/close-registration",
    response_model=APIResponse[OrganizerGatheringStatusView],
)
def close_official_registration(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OrganizerGatheringStatusView]:
    item = organizer.close_registration(db, gathering_id, user.id)
    return APIResponse(
        data=OrganizerGatheringStatusView(id=item.id, status=item.status)
    )


@router.post(
    "/gatherings/{gathering_id}/attendance/{participant_id}",
    response_model=APIResponse[OrganizerAttendanceView],
)
def check_in_participant(
    gathering_id: str,
    participant_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OrganizerAttendanceView]:
    return APIResponse(
        data=OrganizerAttendanceView.model_validate(
            organizer.check_in(db, gathering_id, participant_id, user.id)
        )
    )


@router.post(
    "/templates",
    response_model=APIResponse[OfficialTemplateView],
    status_code=status.HTTP_201_CREATED,
)
def create_official_template(
    body: OfficialTemplateCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OfficialTemplateView]:
    item = organizer.create_template(db, user.id, body)
    return APIResponse(data=OfficialTemplateView.model_validate(item))


@router.get("/templates", response_model=APIResponse[list[OfficialTemplateView]])
def official_templates(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[list[OfficialTemplateView]]:
    return APIResponse(
        data=[OfficialTemplateView.model_validate(item) for item in organizer.list_templates(db, user.id)]
    )


@router.patch(
    "/templates/{template_id}", response_model=APIResponse[OfficialTemplateView]
)
def edit_official_template(
    template_id: str,
    body: OfficialTemplatePatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OfficialTemplateView]:
    return APIResponse(
        data=OfficialTemplateView.model_validate(
            organizer.update_template(db, template_id, user.id, body)
        )
    )


@router.post(
    "/templates/{template_id}/copy",
    response_model=APIResponse[OfficialTemplateView],
    status_code=status.HTTP_201_CREATED,
)
def copy_official_template(
    template_id: str,
    body: OfficialTemplateCopy,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OfficialTemplateView]:
    return APIResponse(
        data=OfficialTemplateView.model_validate(
            organizer.copy_template(db, template_id, user.id, body.title)
        )
    )


@router.delete(
    "/templates/{template_id}", response_model=APIResponse[OfficialTemplateView]
)
def deactivate_official_template(
    template_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OfficialTemplateView]:
    return APIResponse(
        data=OfficialTemplateView.model_validate(
            organizer.deactivate_template(db, template_id, user.id)
        )
    )


@router.post(
    "/templates/{template_id}/instantiate",
    response_model=APIResponse[OfficialGatheringCreatedView],
)
def instantiate_official_template(
    template_id: str,
    body: TemplateInstantiate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[OfficialGatheringCreatedView]:
    item = organizer.instantiate_template(
        db, template_id, user.id, body.start_at, body.quota_batches
    )
    return APIResponse(
        data=OfficialGatheringCreatedView(id=item.id, status=item.status)
    )


@internal_router.post(
    "/trust/{user_id}/organizer-verification",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_admin)],
)
def verify_organizer(
    user_id: str,
    body: OrganizerVerification,
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    profile = organizer.set_organizer_verification(db, user_id, body.verified)
    return APIResponse(
        data={
            "user_id": user_id,
            "organizer_verified": profile.organizer_verified,
            "level": profile.level,
        }
    )
