from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from onemore.core.auth import current_user
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.notify import service
from onemore.modules.notify.schemas import (
    NOTIFICATION_CATEGORIES,
    DeviceDeactivate,
    DeviceInstallationDeactivate,
    DeviceRegister,
    NotificationPreferencesPatch,
    NotificationPreferencesView,
    NotificationView,
)

router = APIRouter(tags=["notify"])


@router.get(
    "/me/notification-preferences",
    response_model=APIResponse[NotificationPreferencesView],
)
def get_notification_preferences(
    user: User = Depends(current_user),
) -> APIResponse[NotificationPreferencesView]:
    return APIResponse(
        data=NotificationPreferencesView.model_validate(service.notification_preferences(user))
    )


@router.patch(
    "/me/notification-preferences",
    response_model=APIResponse[NotificationPreferencesView],
)
def patch_notification_preferences(
    body: NotificationPreferencesPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[NotificationPreferencesView]:
    return APIResponse(
        data=NotificationPreferencesView.model_validate(
            service.update_notification_preferences(db, user, body)
        )
    )


@router.post(
    "/notifications/devices",
    response_model=APIResponse[dict],
    status_code=status.HTTP_201_CREATED,
)
def register_push_device(
    body: DeviceRegister,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    device = service.register_device(db, user.id, body.token, body.platform)
    return APIResponse(
        data={
            "id": device.id,
            "active": device.active,
            "deactivation_token": service.device_deactivation_token(
                user.id, device.token_hash
            ),
        }
    )


@router.delete("/notifications/devices", response_model=APIResponse[dict])
def deactivate_push_device(
    body: DeviceDeactivate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    count = service.deactivate_device(db, user.id, body.token)
    return APIResponse(data={"active": False, "deactivated": count})


@router.delete(
    "/notifications/devices/installation",
    response_model=APIResponse[dict],
)
def deactivate_push_installation(
    body: DeviceInstallationDeactivate,
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    count = service.deactivate_installation(db, body.token, body.deactivation_token)
    return APIResponse(data={"active": False, "deactivated": count})


@router.get("/notifications", response_model=APIResponse[list[NotificationView]])
def notifications(
    limit: int = Query(default=50, ge=1, le=100),
    category: str | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[NotificationView]]:
    if category is not None and category not in NOTIFICATION_CATEGORIES:
        return APIResponse(data=[])
    return APIResponse(
        data=[
            NotificationView.model_validate(item)
            for item in service.list_notifications(
                db, user.id, limit, category=category
            )
        ]
    )
