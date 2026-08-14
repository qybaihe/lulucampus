from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status
from sqlalchemy.orm import Session

from onemore.core.auth import current_user, user_id_from_token
from onemore.core.config import get_settings
from onemore.core.database import SessionLocal, get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.identity import service
from onemore.modules.identity.schemas import (
    DisplayNameChange,
    GrantChange,
    GrantView,
    IdentityFactsView,
    LoginRedemption,
    LoginRedemptionView,
    LoginSessionCreate,
    LoginSessionView,
    MatchingPreferenceChange,
    MatchingPreferenceView,
    PhoneAuthView,
    PhoneLogin,
    PhoneRegister,
    SessionHealthView,
    SocialPreferenceChange,
    SocialPreferenceView,
)

router = APIRouter(tags=["identity"])


def _prepare_login_background(session_id: str) -> None:
    from onemore.hermes.login import login_orchestrator

    login_orchestrator.run(session_id)


def _refresh_timetable_background(user_id: str) -> None:
    from onemore.modules.schedule.orchestrator import refresh_user_timetable

    refresh_user_timetable(user_id)


def _initialize_profile_background(user_id: str) -> None:
    from onemore.modules.profile.service import init_profile

    with SessionLocal() as db:
        init_profile(db, user_id)


@router.post(
    "/auth/register",
    response_model=APIResponse[PhoneAuthView],
    status_code=status.HTTP_201_CREATED,
)
def register_with_phone(
    body: PhoneRegister,
    db: Session = Depends(get_db),
) -> APIResponse[PhoneAuthView]:
    user, access_token = service.register_phone_account(
        db, body.phone, body.password, body.display_name
    )
    return APIResponse(
        data=PhoneAuthView(
            access_token=access_token,
            user_id=user.id,
            display_name=user.display_name,
            is_new_user=True,
        )
    )


@router.post("/auth/login", response_model=APIResponse[PhoneAuthView])
def login_with_phone(
    body: PhoneLogin,
    db: Session = Depends(get_db),
) -> APIResponse[PhoneAuthView]:
    user, access_token = service.login_phone_account(db, body.phone, body.password)
    return APIResponse(
        data=PhoneAuthView(
            access_token=access_token,
            user_id=user.id,
            display_name=user.display_name,
            is_new_user=False,
        )
    )


@router.post(
    "/auth/session",
    response_model=APIResponse[LoginSessionView],
    status_code=status.HTTP_202_ACCEPTED,
)
def create_auth_session(
    body: LoginSessionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> APIResponse[LoginSessionView]:
    settings = get_settings()
    resumed_user_id = None
    if authorization and authorization.lower().startswith("bearer "):
        resumed_user_id = user_id_from_token(authorization[7:].strip())
    elif settings.dev_auth_enabled:
        resumed_user_id = x_user_id or body.resume_user_id
    login, redemption_token = service.create_login_session(
        db, resumed_user_id, body.device_install_id
    )
    if get_settings().hermes_mode == "fake":
        service.prepare_fake_login(db, login.id)
        db.refresh(login)
    elif get_settings().is_production:
        from onemore.tasks.celery_app import celery_app

        celery_app.send_task("onemore.identity.login", args=[login.id])
    else:
        background_tasks.add_task(_prepare_login_background, login.id)
    return APIResponse(
        data=LoginSessionView(
            id=login.id,
            user_id=login.user_id,
            status=login.status,
            qr_image_data_url=login.qr_image_data_url,
            deep_link=login.deep_link,
            expires_at=login.expires_at,
            redemption_token=redemption_token,
            error_category=login.error_category,
        ),
        meta={"poll_after_seconds": 2, "timeout_seconds": 200},
    )


@router.get("/auth/session/{session_id}", response_model=APIResponse[LoginSessionView])
def poll_auth_session(
    session_id: str,
    x_login_redemption: str = Header(alias="X-Login-Redemption", min_length=32),
    db: Session = Depends(get_db),
) -> APIResponse[LoginSessionView]:
    login = service.get_login_session(db, session_id, x_login_redemption)
    return APIResponse(
        data=LoginSessionView(
            id=login.id,
            user_id=login.user_id,
            status=login.status,
            qr_image_data_url=login.qr_image_data_url,
            deep_link=login.deep_link,
            expires_at=login.expires_at,
            error_category=login.error_category,
        ),
        meta={"poll_after_seconds": 2},
    )


@router.post("/auth/session/{session_id}/cancel", response_model=APIResponse[LoginSessionView])
def cancel_auth_session(
    session_id: str,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_login_redemption: str = Header(alias="X-Login-Redemption", min_length=32),
) -> APIResponse[LoginSessionView]:
    login = service.cancel_login_session(
        db, session_id, x_login_redemption, x_user_id
    )
    return APIResponse(
        data=LoginSessionView(
            id=login.id,
            user_id=login.user_id,
            status=login.status,
            qr_image_data_url=login.qr_image_data_url,
            deep_link=login.deep_link,
            expires_at=login.expires_at,
            error_category=login.error_category,
        )
    )


@router.post(
    "/auth/session/{session_id}/redeem",
    response_model=APIResponse[LoginRedemptionView],
)
def redeem_auth_session(
    session_id: str,
    body: LoginRedemption,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db),
) -> APIResponse[LoginRedemptionView]:
    access_token = service.redeem_login_session(
        db, session_id, body.redemption_token, idempotency_key
    )
    return APIResponse(data=LoginRedemptionView(access_token=access_token))


@router.post("/auth/session/{session_id}/demo-complete", include_in_schema=False)
def demo_complete_auth(
    session_id: str,
    x_login_redemption: str = Header(alias="X-Login-Redemption", min_length=32),
    x_demo_campus_subject: str = Header(
        default="demo-default", alias="X-Demo-Campus-Subject", min_length=3, max_length=128
    ),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    if not get_settings().dev_auth_enabled:
        return APIResponse(data={"status": "disabled"})
    service.get_login_session(db, session_id, x_login_redemption)
    service.complete_fake_login(db, session_id, x_demo_campus_subject)
    return APIResponse(data={"status": "SUCCESS"})


@router.post("/auth/grants", response_model=APIResponse[GrantView])
def update_grant(
    body: GrantChange,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GrantView]:
    grant = service.change_grant(db, user.id, body.scope, body.granted)
    if body.scope == "timetable" and body.granted:
        if get_settings().is_production:
            from onemore.tasks.celery_app import celery_app

            celery_app.send_task("onemore.schedule.refresh_user", args=[user.id])
        else:
            background_tasks.add_task(_refresh_timetable_background, user.id)
    if body.scope in {"curriculum", "enrollment"} and body.granted:
        if get_settings().is_production:
            from onemore.tasks.celery_app import celery_app

            celery_app.send_task("onemore.profile.initialize", args=[user.id])
        else:
            background_tasks.add_task(_initialize_profile_background, user.id)
    return APIResponse(data=GrantView.model_validate(grant))


def _identity_facts_view(db: Session, user: User) -> IdentityFactsView:
    current, grants, health = service.identity_facts(db, user.id)
    return IdentityFactsView(
        user_id=current.id,
        display_name=current.display_name,
        verified=current.verified_at is not None,
        college=current.college,
        major=current.major,
        grade_year=current.grade_year,
        campus=current.campus,
        gender_code=current.gender_code,
        social_enabled=current.social_enabled,
        course_matching_enabled=current.course_matching_enabled,
        identity_disclosure=current.identity_disclosure,
        same_gender_only=current.same_gender_only,
        minimum_group_size=current.minimum_group_size,
        scene_sensitive_policy="mute_onsite",
        grants=[GrantView.model_validate(item) for item in grants],
        session_health=[SessionHealthView.model_validate(item) for item in health],
    )


@router.get("/auth/me", response_model=APIResponse[IdentityFactsView])
def get_my_identity(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[IdentityFactsView]:
    return APIResponse(data=_identity_facts_view(db, user))


@router.patch("/me/display-name", response_model=APIResponse[IdentityFactsView])
def update_my_display_name(
    body: DisplayNameChange,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[IdentityFactsView]:
    service.update_display_name(db, user, body.display_name)
    return APIResponse(data=_identity_facts_view(db, user))


@router.get("/me/privacy", response_model=APIResponse[SocialPreferenceView])
def get_social_preferences(
    user: User = Depends(current_user),
) -> APIResponse[SocialPreferenceView]:
    return APIResponse(
        data=SocialPreferenceView.model_validate(service.social_preferences(user))
    )


@router.patch("/me/privacy", response_model=APIResponse[SocialPreferenceView])
def update_social_preferences(
    body: SocialPreferenceChange,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[SocialPreferenceView]:
    if body.same_gender_only and (user.gender_code or "").lower() in {
        "",
        "unknown",
        "unspecified",
    }:
        from onemore.core.errors import AppError

        raise AppError("VERIFIED_GENDER_REQUIRED", "同性局偏好需要已核验的身份信息", 422)
    updated = service.update_social_preferences(
        db, user, body.model_dump(exclude_none=True)
    )
    return APIResponse(data=SocialPreferenceView.model_validate(updated))


@router.get(
    "/me/matching-preferences",
    response_model=APIResponse[MatchingPreferenceView],
)
def get_matching_preferences(
    user: User = Depends(current_user),
) -> APIResponse[MatchingPreferenceView]:
    return APIResponse(
        data=MatchingPreferenceView.model_validate(
            service.matching_preferences(user)
        )
    )


@router.patch(
    "/me/matching-preferences",
    response_model=APIResponse[MatchingPreferenceView],
)
def update_matching_preferences(
    body: MatchingPreferenceChange,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[MatchingPreferenceView]:
    return APIResponse(
        data=MatchingPreferenceView.model_validate(
            service.update_matching_preferences(
                db, user, body.model_dump(exclude_none=True)
            )
        )
    )
