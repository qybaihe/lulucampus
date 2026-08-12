from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.auth import current_user
from onemore.core.config import get_settings
from onemore.core.database import SessionLocal, get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import CapabilityTag, TrustLevel, User
from onemore.modules.profile import service
from onemore.modules.profile.schemas import (
    CapabilityOptionView,
    CapabilityView,
    ProfileInitRequest,
    ProfileView,
    SelfReportedTagsPatch,
)

router = APIRouter(tags=["profile"])


def _initialize_background(user_id: str) -> None:
    with SessionLocal() as db:
        service.init_profile(db, user_id)


def _profile_view(db: Session, user: User) -> ProfileView:
    current, profile, trust = service.get_profile_data(db, user.id)
    labels = {row.key: row.label for row in db.scalars(select(CapabilityTag))}
    capabilities = [
        CapabilityView(
            key=key,
            label=labels.get(key, key),
            source="verified",
            weight=profile.capability_vector.get(key, 0.0),
            hidden=key in profile.hidden_verified_tags,
        )
        for key in profile.verified_tags
    ]
    capabilities.extend(
        CapabilityView(
            key=key,
            label=labels.get(key, key),
            source="self_reported",
            weight=profile.capability_vector.get(key, 0.0),
        )
        for key in profile.self_reported_tags
        if key not in profile.verified_tags and not str(key).startswith("taste:")
    )
    from onemore.db.models import TasteProfile
    from onemore.modules.taste_profile.service import TASTE_TAG_PREFIX, taste_summary

    taste = db.get(TasteProfile, user.id)
    if taste is not None:
        primary = taste.primary_tag or {}
        if isinstance(primary, dict) and primary.get("key"):
            key = f"{TASTE_TAG_PREFIX}{primary['key']}"
            capabilities.append(
                CapabilityView(
                    key=key,
                    label=str(primary.get("label") or primary["key"]),
                    source="taste",
                    weight=float(profile.capability_vector.get(key, primary.get("score") or 0.7)),
                )
            )
        for tag in taste.secondary_tags or []:
            if not isinstance(tag, dict) or not tag.get("key"):
                continue
            key = f"{TASTE_TAG_PREFIX}{tag['key']}"
            capabilities.append(
                CapabilityView(
                    key=key,
                    label=str(tag.get("label") or tag["key"]),
                    source="taste",
                    weight=float(profile.capability_vector.get(key, tag.get("score") or 0.5)),
                )
            )

    return ProfileView(
        user_id=current.id,
        init_status=profile.init_status,
        init_progress=profile.init_progress,
        identity={
            "college": current.college,
            "major": current.major,
            "grade_year": current.grade_year,
            "campus": current.campus,
            "gender_code": current.gender_code,
            "source": "school_record",
            "editable": False,
        },
        capabilities=capabilities,
        available_capabilities=[
            CapabilityOptionView(key=key, label=label)
            for key, label in sorted(labels.items())
        ],
        interest_domains=profile.interest_domains,
        cross_major_score=profile.cross_major_score,
        trust_progress={"level": trust.level if trust else TrustLevel.T0.value},
        taste_profile=taste_summary(db, user.id),
    )


@router.get("/profile/me", response_model=APIResponse[ProfileView])
def get_my_profile(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[ProfileView]:
    return APIResponse(data=_profile_view(db, user))


@router.post(
    "/profile/init",
    response_model=APIResponse[ProfileView],
    status_code=status.HTTP_202_ACCEPTED,
)
def initialize_profile(
    body: ProfileInitRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ProfileView]:
    profile = service.begin_profile_init(db, user.id, force=body.force)
    should_schedule = profile.init_status != "ready" or body.force
    if should_schedule:
        if get_settings().is_production:
            from onemore.tasks.celery_app import celery_app

            celery_app.send_task("onemore.profile.initialize", args=[user.id])
        else:
            background_tasks.add_task(_initialize_background, user.id)
    return APIResponse(
        data=_profile_view(db, user),
        meta={"background": should_schedule, "poll": "/profile/me"},
    )


@router.patch("/profile/tags", response_model=APIResponse[ProfileView])
def patch_profile_tags(
    body: SelfReportedTagsPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ProfileView]:
    service.edit_self_reported_tags(db, user.id, body.tags, body.hidden_verified_tags)
    return APIResponse(data=_profile_view(db, user))
