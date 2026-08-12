from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onemore.core.errors import ConflictError, ForbiddenError, NotFoundError
from onemore.core.locks import gathering_locks
from onemore.core.time import ensure_utc
from onemore.db.models import (
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    OfficialGatheringTemplate,
    OrganizerAttendance,
    TrustLevel,
    TrustProfile,
    User,
)
from onemore.modules.gathering.organizer_schemas import (
    OfficialGatheringCreate,
    OfficialTemplateCreate,
    OfficialTemplatePatch,
)
from onemore.modules.gathering.state_machine import GatheringEvent, transition
from onemore.modules.trust import service as trust_service


def set_organizer_verification(db: Session, user_id: str, verified: bool) -> TrustProfile:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", user_id)
    profile = trust_service.ensure_trust_profile(db, user_id)
    profile.organizer_verified = verified
    if verified:
        profile.level = TrustLevel.T4.value
    db.commit()
    if not verified:
        return trust_service.recompute_level(db, user_id)
    return profile


def _require_owner(db: Session, gathering_id: str, user_id: str) -> Gathering:
    gathering = db.get(Gathering, gathering_id)
    if gathering is None or not gathering.is_official:
        raise NotFoundError("官方局", gathering_id)
    if gathering.owner_user_id != user_id:
        raise ForbiddenError("只有创建该官方局的主理人可访问管理台")
    trust_service.require_unlock(db, user_id, "organizer_console")
    return gathering


def create_official(db: Session, user_id: str, body: OfficialGatheringCreate) -> Gathering:
    trust_service.require_unlock(db, user_id, "official_gathering")
    now = datetime.now(UTC)
    start_at = ensure_utc(body.start_at)
    if start_at <= now:
        raise ConflictError("START_TIME_IN_PAST", "官方局开始时间必须晚于当前时间")
    gathering = Gathering(
        owner_user_id=user_id,
        gathering_type=body.gathering_type,
        mode="similar",
        title=body.title,
        goal=body.goal,
        status=GatheringStatus.POOLING.value,
        min_size=body.min_size,
        target_size=body.target_size,
        required_trust_level=(
            TrustLevel.T2.value if body.min_size <= 2 else TrustLevel.T1.value
        ),
        campus=body.campus,
        same_gender_only=False,
        identity_disclosure="after_confirmed",
        start_at=start_at,
        end_at=ensure_utc(body.end_at),
        location=body.location,
        required_roles=body.required_roles,
        is_official=True,
        official_metadata={
            "quota_batches": [item.model_dump() for item in body.quota_batches],
            "created_via": "organizer_console",
        },
        expires_at=max(now + timedelta(minutes=5), start_at - timedelta(minutes=30)),
    )
    db.add(gathering)
    db.flush()
    db.add(
        GatheringMember(
            gathering_id=gathering.id,
            user_id=user_id,
            joined_via="owner",
        )
    )
    db.commit()
    db.refresh(gathering)
    return gathering


def list_official(db: Session, user_id: str) -> list[Gathering]:
    trust_service.require_unlock(db, user_id, "organizer_console")
    return list(
        db.scalars(
            select(Gathering)
            .where(Gathering.owner_user_id == user_id, Gathering.is_official.is_(True))
            .order_by(Gathering.start_at.desc())
        )
    )


def dashboard(db: Session, gathering_id: str, user_id: str) -> dict:
    gathering = _require_owner(db, gathering_id, user_id)
    members = list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.left_at.is_(None),
            )
        )
    )
    attended = set(
        db.scalars(
            select(OrganizerAttendance.user_id).where(
                OrganizerAttendance.gathering_id == gathering.id
            )
        )
    )
    identities_visible = gathering.status in {
        GatheringStatus.CONFIRMED.value,
        GatheringStatus.PREVIEWED.value,
        GatheringStatus.EXECUTED.value,
        GatheringStatus.ACTIVE.value,
        GatheringStatus.COMPLETED.value,
        GatheringStatus.ARCHIVED.value,
    }
    participants = None
    if identities_visible:
        participants = []
        for member in members:
            user = db.get(User, member.user_id)
            participants.append(
                {
                    "user_id": member.user_id,
                    "display_name": user.display_name if user else None,
                    "confirmation_status": member.confirmation_status,
                    "attended": member.user_id in attended,
                }
            )
    return {
        "gathering_id": gathering.id,
        "status": gathering.status,
        "target_size": gathering.target_size,
        "registered_count": len(members),
        "confirmed_count": sum(
            item.confirmation_status == ConfirmationStatus.CONFIRMED.value for item in members
        ),
        "attended_count": len(attended),
        "quota_batches": gathering.official_metadata.get("quota_batches", []),
        "participants": participants,
        "identity_visibility": "after_confirmed",
    }


def finalize_official(db: Session, gathering_id: str, owner_id: str) -> Gathering:
    with gathering_locks.acquire(gathering_id):
        return _finalize_official_locked(db, gathering_id, owner_id)


def close_registration(db: Session, gathering_id: str, owner_id: str) -> Gathering:
    with gathering_locks.acquire(gathering_id):
        gathering = _require_owner(db, gathering_id, owner_id)
        if gathering.status == GatheringStatus.TENTATIVE.value:
            return gathering
        if gathering.status != GatheringStatus.POOLING.value:
            raise ConflictError("REGISTRATION_NOT_OPEN", "当前官方局不在报名状态")
        member_count = (
            db.scalar(
                select(func.count(GatheringMember.id)).where(
                    GatheringMember.gathering_id == gathering.id,
                    GatheringMember.left_at.is_(None),
                )
            )
            or 0
        )
        if member_count < gathering.min_size:
            raise ConflictError(
                "MINIMUM_NOT_REACHED",
                "报名人数尚未达到最低成局人数",
                {"registered_count": member_count, "minimum": gathering.min_size},
            )
        transition(db, gathering, GatheringEvent.MATCHED, actor_user_id=owner_id)
        db.commit()
        return gathering


def _finalize_official_locked(db: Session, gathering_id: str, owner_id: str) -> Gathering:
    gathering = _require_owner(db, gathering_id, owner_id)
    if gathering.status == GatheringStatus.EXECUTED.value:
        return gathering
    if gathering.status != GatheringStatus.CONFIRMED.value:
        raise ConflictError("OFFICIAL_NOT_CONFIRMED", "官方局尚未完成全员确认")
    members = list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.left_at.is_(None),
            )
        )
    )
    if len(members) < gathering.min_size or not all(
        member.confirmation_status == ConfirmationStatus.CONFIRMED.value for member in members
    ):
        raise ConflictError("ALL_MEMBERS_NOT_CONFIRMED", "必须由全体成员分别确认")
    transition(db, gathering, GatheringEvent.PREVIEW_CREATED, actor_user_id=owner_id)
    transition(db, gathering, GatheringEvent.ACTION_SUCCEEDED, actor_user_id=owner_id)
    from onemore.modules.collab.service import exit_protocol
    from onemore.modules.notify.service import sync_calendar

    exit_protocol(db, gathering.id)
    sync_calendar(db, gathering.id)
    db.commit()
    return gathering


def check_in(db: Session, gathering_id: str, participant_id: str, owner_id: str) -> dict:
    gathering = _require_owner(db, gathering_id, owner_id)
    if gathering.status not in {
        GatheringStatus.EXECUTED.value,
        GatheringStatus.ACTIVE.value,
        GatheringStatus.COMPLETED.value,
    }:
        raise ConflictError("CHECK_IN_NOT_OPEN", "到场登记仅在执行成功后开放")
    if gathering.start_at is None or gathering.end_at is None:
        raise ConflictError("CHECK_IN_WINDOW_UNKNOWN", "本局缺少可验证的到场时间")
    now = datetime.now(UTC)
    opens_at = ensure_utc(gathering.start_at) - timedelta(minutes=30)
    closes_at = ensure_utc(gathering.end_at) + timedelta(hours=24)
    if now < opens_at or now > closes_at:
        raise ConflictError(
            "CHECK_IN_WINDOW_CLOSED",
            "到场登记仅在开始前 30 分钟至结束后 24 小时开放",
            {"opens_at": opens_at.isoformat(), "closes_at": closes_at.isoformat()},
        )
    member = db.scalar(
        select(GatheringMember).where(
            GatheringMember.gathering_id == gathering.id,
            GatheringMember.user_id == participant_id,
            GatheringMember.left_at.is_(None),
        )
    )
    if member is None:
        raise NotFoundError("局成员", participant_id)
    attendance = db.scalar(
        select(OrganizerAttendance).where(
            OrganizerAttendance.gathering_id == gathering.id,
            OrganizerAttendance.user_id == participant_id,
        )
    )
    if attendance is None:
        attendance = OrganizerAttendance(
            gathering_id=gathering.id,
            user_id=participant_id,
        )
        db.add(attendance)
    # Check-in is an attendance fact, not an early completion verdict.  Trust
    # and completion are adjudicated only after the activity's end boundary.
    from onemore.modules.collab.service import record_goal_member_progress

    record_goal_member_progress(
        db, gathering.id, participant_id, source="organizer_check_in"
    )
    db.commit()
    return {"user_id": participant_id, "attended": True}


def create_template(
    db: Session, user_id: str, body: OfficialTemplateCreate
) -> OfficialGatheringTemplate:
    trust_service.require_unlock(db, user_id, "organizer_console")
    template = OfficialGatheringTemplate(owner_user_id=user_id, **body.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def list_templates(db: Session, user_id: str) -> list[OfficialGatheringTemplate]:
    trust_service.require_unlock(db, user_id, "organizer_console")
    return list(
        db.scalars(
            select(OfficialGatheringTemplate)
            .where(
                OfficialGatheringTemplate.owner_user_id == user_id,
                OfficialGatheringTemplate.active.is_(True),
            )
            .order_by(OfficialGatheringTemplate.updated_at.desc())
        )
    )


def get_template(
    db: Session, template_id: str, user_id: str, *, active_only: bool = False
) -> OfficialGatheringTemplate:
    trust_service.require_unlock(db, user_id, "organizer_console")
    template = db.get(OfficialGatheringTemplate, template_id)
    if (
        template is None
        or template.owner_user_id != user_id
        or (active_only and not template.active)
    ):
        raise NotFoundError("官方局模板", template_id)
    return template


def update_template(
    db: Session, template_id: str, user_id: str, patch: OfficialTemplatePatch
) -> OfficialGatheringTemplate:
    template = get_template(db, template_id, user_id, active_only=True)
    current = {
        field: getattr(template, field)
        for field in OfficialTemplateCreate.model_fields
    }
    current.update(patch.model_dump(exclude_unset=True))
    validated = OfficialTemplateCreate.model_validate(current)
    if validated.min_size > validated.target_size:
        raise ConflictError("INVALID_GROUP_SIZE", "最低人数不能超过目标人数")
    for field, value in validated.model_dump().items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


def copy_template(
    db: Session, template_id: str, user_id: str, title: str | None
) -> OfficialGatheringTemplate:
    source = get_template(db, template_id, user_id)
    values = {
        field: getattr(source, field)
        for field in OfficialTemplateCreate.model_fields
    }
    values["title"] = title or f"{source.title}（副本）"
    return create_template(db, user_id, OfficialTemplateCreate.model_validate(values))


def deactivate_template(
    db: Session, template_id: str, user_id: str
) -> OfficialGatheringTemplate:
    template = get_template(db, template_id, user_id)
    template.active = False
    db.commit()
    db.refresh(template)
    return template


def instantiate_template(
    db: Session,
    template_id: str,
    user_id: str,
    start_at: datetime,
    quota_batches: list,
) -> Gathering:
    template = get_template(db, template_id, user_id, active_only=True)
    body = OfficialGatheringCreate(
        title=template.title,
        goal=template.goal,
        gathering_type=template.gathering_type,
        start_at=start_at,
        end_at=ensure_utc(start_at) + timedelta(minutes=template.duration_minutes),
        location=template.location,
        campus=template.campus,
        min_size=template.min_size,
        target_size=template.target_size,
        required_roles=template.required_roles,
        quota_batches=quota_batches,
    )
    return create_official(db, user_id, body)
