from __future__ import annotations

import shutil
from contextlib import ExitStack
from pathlib import Path

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.errors import AppError, NotFoundError
from onemore.core.locks import user_locks
from onemore.db.models import (
    ActionStatus,
    Assignment,
    AuthorizationGrant,
    CampusAction,
    Channel,
    ChannelParticipant,
    ChannelStatus,
    Enrollment,
    Gathering,
    GatheringMember,
    GatheringStatus,
    IdempotencyRecord,
    IntentCard,
    LoginSession,
    MediaAsset,
    MediaChannelGrant,
    Message,
    Notification,
    OfficialGatheringTemplate,
    OrganizerAttendance,
    Profile,
    PushDevice,
    Relation,
    RelationStatus,
    SceneTrigger,
    SecurityEvent,
    SessionHealth,
    TimeWindow,
    TrustAppeal,
    TrustEvent,
    TrustProfile,
    User,
    UserBlock,
    utcnow,
)
from onemore.hermes.vault import vault_manager


def list_blocks(db: Session, user_id: str) -> list[dict]:
    rows = list(
        db.scalars(
            select(UserBlock)
            .where(UserBlock.blocker_id == user_id)
            .order_by(UserBlock.created_at.desc())
        )
    )
    return [{"blocked_user_id": item.blocked_id, "created_at": item.created_at} for item in rows]


def block_user(db: Session, user_id: str, blocked_user_id: str) -> UserBlock:
    if user_id == blocked_user_id:
        raise AppError("INVALID_BLOCK", "不能屏蔽自己", 422)
    target = db.get(User, blocked_user_id)
    if target is None or target.account_status != "active":
        raise NotFoundError("用户", blocked_user_id)
    with ExitStack() as stack:
        for locked_user_id in sorted((user_id, blocked_user_id)):
            stack.enter_context(user_locks.acquire(locked_user_id))
        item = db.scalar(
            select(UserBlock).where(
                UserBlock.blocker_id == user_id,
                UserBlock.blocked_id == blocked_user_id,
            )
        )
        if item is None:
            item = UserBlock(blocker_id=user_id, blocked_id=blocked_user_id)
            db.add(item)
            db.commit()
            db.refresh(item)
    return item


def unblock_user(db: Session, user_id: str, blocked_user_id: str) -> None:
    db.execute(
        delete(UserBlock).where(
            UserBlock.blocker_id == user_id,
            UserBlock.blocked_id == blocked_user_id,
        )
    )
    db.commit()


def export_user_data(db: Session, user_id: str) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", user_id)
    profile = db.get(Profile, user_id)
    grants = list(
        db.scalars(select(AuthorizationGrant).where(AuthorizationGrant.user_id == user_id))
    )
    intents = list(db.scalars(select(IntentCard).where(IntentCard.user_id == user_id)))
    gathering_rows = db.execute(
        select(Gathering.id, Gathering.title, Gathering.status, Gathering.completed_at)
        .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
        .where(GatheringMember.user_id == user_id)
    ).all()
    notifications = list(db.scalars(select(Notification).where(Notification.user_id == user_id)))
    return {
        "exported_at": utcnow(),
        "identity": {
            "user_id": user.id,
            "display_name": user.display_name,
            "college": user.college,
            "major": user.major,
            "grade_year": user.grade_year,
            "campus": user.campus,
            "gender_code": user.gender_code,
            "verified_at": user.verified_at,
        },
        "privacy_preferences": {
            "social_enabled": user.social_enabled,
            "course_matching_enabled": user.course_matching_enabled,
            "calendar_enabled": user.calendar_enabled,
            "notification_enabled": user.notification_enabled,
            "identity_disclosure": user.identity_disclosure,
            "same_gender_only": user.same_gender_only,
            "minimum_group_size": user.minimum_group_size,
            "matching_preferences": user.matching_preferences,
        },
        "grants": [
            {"scope": item.scope, "granted": item.granted, "granted_at": item.granted_at}
            for item in grants
        ],
        "profile": (
            {
                "verified_tags": profile.verified_tags,
                "self_reported_tags": profile.self_reported_tags,
                "hidden_verified_tags": profile.hidden_verified_tags,
                "capability_vector": profile.capability_vector,
                "interest_domains": profile.interest_domains,
                "cross_major_score": profile.cross_major_score,
            }
            if profile
            else None
        ),
        "intents": [
            {
                "id": item.id,
                "status": item.status,
                "gathering_type": item.gathering_type,
                "goal": item.goal,
                "created_at": item.created_at,
            }
            for item in intents
        ],
        "gatherings": [
            {
                "id": row.id,
                "title": row.title,
                "status": row.status,
                "completed_at": row.completed_at,
            }
            for row in gathering_rows
        ],
        "notifications": [
            {"type": item.type, "payload": item.payload, "created_at": item.created_at}
            for item in notifications
        ],
        "blocks": list_blocks(db, user_id),
    }


def deactivate_account(db: Session, user_id: str) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", user_id)
    active_memberships = list(
        db.scalars(
            select(GatheringMember)
            .join(Gathering, Gathering.id == GatheringMember.gathering_id)
            .where(
                GatheringMember.user_id == user_id,
                GatheringMember.left_at.is_(None),
                Gathering.status.in_(
                    [
                        GatheringStatus.DRAFT.value,
                        GatheringStatus.POOLING.value,
                        GatheringStatus.TENTATIVE.value,
                        GatheringStatus.CONFIRMED.value,
                        GatheringStatus.PREVIEWED.value,
                        GatheringStatus.EXECUTED.value,
                        GatheringStatus.ACTIVE.value,
                    ]
                ),
            )
        )
    )
    from onemore.modules.gathering.service import leave

    for membership in active_memberships:
        leave(db, membership.gathering_id, user_id, reason="account_deleted")

    media_assets = list(
        db.scalars(select(MediaAsset).where(MediaAsset.owner_user_id == user_id))
    )
    media_ids = [asset.id for asset in media_assets]
    if media_ids:
        db.execute(delete(MediaChannelGrant).where(MediaChannelGrant.media_id.in_(media_ids)))
        db.execute(delete(MediaAsset).where(MediaAsset.id.in_(media_ids)))

    db.execute(
        update(Gathering).where(Gathering.owner_user_id == user_id).values(owner_user_id=None)
    )
    db.execute(
        update(Gathering)
        .where(
            Gathering.source_intent_id.in_(
                select(IntentCard.id).where(IntentCard.user_id == user_id)
            )
        )
        .values(source_intent_id=None)
    )
    for model in (
        Assignment,
        AuthorizationGrant,
        ChannelParticipant,
        Enrollment,
        IdempotencyRecord,
        LoginSession,
        Notification,
        OrganizerAttendance,
        Profile,
        PushDevice,
        SceneTrigger,
        SessionHealth,
        TimeWindow,
        TrustAppeal,
        TrustEvent,
        TrustProfile,
    ):
        column = model.user_id
        db.execute(delete(model).where(column == user_id))
    db.execute(
        delete(OfficialGatheringTemplate).where(OfficialGatheringTemplate.owner_user_id == user_id)
    )
    db.execute(delete(IntentCard).where(IntentCard.user_id == user_id))
    db.execute(
        update(CampusAction)
        .where(CampusAction.user_id == user_id)
        .values(
            params={},
            preview_snapshot={},
            execution_result={"redacted": True},
            status=ActionStatus.INVALIDATED.value,
        )
    )
    db.execute(
        update(Message)
        .where(Message.sender_id == user_id)
        .values(sender_id="deleted-user", content="[已注销用户消息]")
    )
    relation_ids = select(Relation.id).where(
        or_(Relation.participant_a_id == user_id, Relation.participant_b_id == user_id)
    )
    db.execute(
        update(Channel)
        .where(Channel.relation_id.in_(relation_ids))
        .values(status=ChannelStatus.CLOSED.value)
    )
    db.execute(
        update(Relation)
        .where(or_(Relation.participant_a_id == user_id, Relation.participant_b_id == user_id))
        .values(status=RelationStatus.DISSOLVED.value, dissolved_by=user_id, dissolved_at=utcnow())
    )
    db.execute(
        update(SecurityEvent)
        .where(SecurityEvent.user_id == user_id)
        .values(user_id=None, details={"redacted": True})
    )
    user.netid_hash = None
    user.display_name = "已注销同学"
    user.college = None
    user.major = None
    user.grade_year = None
    user.campus = None
    user.gender_code = None
    user.verified_at = None
    user.social_enabled = False
    user.course_matching_enabled = False
    user.calendar_enabled = False
    user.notification_enabled = False
    user.account_status = "deleted"
    user.deleted_at = utcnow()
    db.commit()
    vault_manager.purge_user(user_id)
    # Remove only the account-owned subtree below the configured media root.
    # Database grants/metadata are committed first, so a filesystem failure
    # can never leave downloadable private media behind.
    media_root = get_settings().media_root.resolve()
    user_media_root = (media_root / user_id).resolve()
    if user_media_root != media_root and user_media_root.is_relative_to(media_root):
        shutil.rmtree(user_media_root, ignore_errors=True)
    for asset in media_assets:
        path = Path(asset.storage_path).resolve()
        if path.is_relative_to(media_root):
            path.unlink(missing_ok=True)
