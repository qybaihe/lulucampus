from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import event, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.errors import AppError, ConflictError, NotFoundError
from onemore.core.time import ensure_utc
from onemore.db.models import (
    Gathering,
    GatheringMember,
    GatheringStatus,
    Notification,
    PushDelivery,
    PushDevice,
    TrustEvent,
    User,
)
from onemore.modules.notify.provider import get_push_provider
from onemore.modules.notify.schemas import NotificationPreferencesPatch

ALLOWED_NOTIFICATION_TYPES = {
    "confirmation_required",
    "authorization_required",
    "execution_succeeded",
    "gathering_reminder",
    "backfill_invitation",
    "silent_dissolution",
    "reauthorization_required",
    "trust_level_changed",
    "chat_message",
    "calendar_revoked",
    "competition_deadline",
    "completion_confirmation",
    "gathering_rescheduled",
    "reschedule_vote_required",
    "reschedule_vote_rejected",
    "action_modification_requested",
    "relation_ready",
}

DEFAULT_NOTIFICATION_PREFERENCES = {
    "gathering_updates": True,
    "action_updates": True,
    "chat_messages": True,
    "trust_updates": True,
    "competition_deadlines": True,
}
SYSTEM_SETTINGS_MANAGED_LOCALLY = [
    "notification_authorization",
    "calendar_authorization",
    "focus_mode",
]

APNS_ROUTE_KEYS = {
    "action_id",
    "appeal",
    "calendar_event",
    "channel_id",
    "competition_id",
    "deep_link",
    "gathering_id",
    "intent_card_id",
    "remove_event",
    "screen_id",
    "share_token",
    "relation_id",
}


def _push_token_key(key_id: str) -> bytes:
    settings = get_settings()
    secret = settings.push_token_encryption_keys.get(key_id)
    if secret is None and not settings.is_production and key_id == settings.push_token_key_id:
        # Local/test fallback remains isolated from production validation and is
        # still distinct from the stored ciphertext and searchable token hash.
        secret = f"dev-push-token:{settings.auth_signing_key}"
    if secret is None:
        raise AppError("PUSH_TOKEN_KEY_UNAVAILABLE", "设备令牌加密密钥不可用", 503)
    return hashlib.sha256(secret.encode()).digest()


def encrypt_device_token(token: str, key_id: str | None = None) -> tuple[str, str]:
    selected_key_id = key_id or get_settings().push_token_key_id
    nonce = secrets.token_bytes(12)
    aad = f"onemore-apns-token:{selected_key_id}".encode()
    encrypted = AESGCM(_push_token_key(selected_key_id)).encrypt(
        nonce, token.encode(), aad
    )
    return base64.urlsafe_b64encode(nonce + encrypted).decode(), selected_key_id


def decrypt_device_token(device: PushDevice) -> str:
    if device.token_ciphertext is None or device.token_key_id is None:
        raise ValueError("legacy device token is not recoverable")
    raw = base64.urlsafe_b64decode(device.token_ciphertext.encode())
    if len(raw) < 29:
        raise ValueError("invalid encrypted device token")
    aad = f"onemore-apns-token:{device.token_key_id}".encode()
    decrypted = AESGCM(_push_token_key(device.token_key_id)).decrypt(
        raw[:12], raw[12:], aad
    )
    return decrypted.decode()


def apns_payload(notification: Notification) -> dict:
    source = notification.payload or {}
    summary = source.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = {
            "confirmation_required": "有一场组局等待你确认",
            "authorization_required": "噜噜需要你确认下一步操作",
            "execution_succeeded": "行动已完成",
            "gathering_reminder": "组局即将开始",
            "backfill_invitation": "有一个适合你的补位邀请",
            "silent_dissolution": "本次组局未能成局",
            "reauthorization_required": "操作条件变化，请重新确认",
            "trust_level_changed": "信用进度有更新",
            "chat_message": "会话有新消息",
            "calendar_revoked": "日历中的组局安排已撤销",
            "competition_deadline": "比赛节点临近",
            "completion_confirmation": "请确认本次组局完成情况",
            "gathering_rescheduled": "组局时间有调整",
            "reschedule_vote_required": "有一项匿名改约提议等待你确认",
            "reschedule_vote_rejected": "本次改约提议未通过",
            "action_modification_requested": "行动预览需要调整",
            "relation_ready": "一段新的搭子关系已建立",
        }.get(notification.type, "你有一条新通知")
    result: dict = {
        "aps": {
            "alert": {"title": "噜噜成局", "body": summary[:180]},
            "sound": "default",
            "category": notification.type,
        },
        "notification_id": notification.id,
        "type": notification.type,
    }
    for key in APNS_ROUTE_KEYS:
        value = source.get(key)
        if isinstance(value, (str, bool, int, float, dict, list)):
            result[key] = value
    thread_id = source.get("channel_id") or source.get("gathering_id")
    if isinstance(thread_id, str):
        result["aps"]["thread-id"] = thread_id
    # APNs rejects payloads above 4 KiB. Calendar details are useful but not
    # essential to routing, so remove them first instead of truncating JSON.
    if len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode()) > 4096:
        result.pop("calendar_event", None)
    return result


def _enqueue_notification_delivery(db: Session, notification: Notification) -> None:
    if notification.payload.get("push_delivery_suppressed") is True:
        return
    devices = list(
        db.scalars(
            select(PushDevice).where(
                PushDevice.user_id == notification.user_id,
                PushDevice.active.is_(True),
                PushDevice.token_ciphertext.is_not(None),
            )
        )
    )
    for device in devices:
        db.add(
            PushDelivery(
                notification_id=notification.id,
                device_id=device.id,
                status="pending",
                next_attempt_at=datetime.now(UTC),
            )
        )
    if devices:
        db.info["push_outbox_pending"] = True


def drain_push_outbox(db: Session, limit: int = 100) -> dict[str, int]:
    """Deliver committed outbox rows with bounded exponential retries.

    The business transaction only inserts ``PushDelivery`` rows. This worker
    runs after commit (inline for the deterministic fake provider; Celery/beat
    for APNs), so provider downtime can never roll back a chat or gathering
    state transition.
    """

    now = datetime.now(UTC)
    attempts = list(
        db.scalars(
            select(PushDelivery)
            .where(
                PushDelivery.status.in_(["pending", "retryable"]),
                PushDelivery.next_attempt_at <= now,
                PushDelivery.attempt_count < 5,
            )
            .order_by(PushDelivery.next_attempt_at, PushDelivery.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    if not attempts:
        return {"processed": 0, "delivered": 0, "retryable": 0, "invalidated": 0}
    counts = {"processed": 0, "delivered": 0, "retryable": 0, "invalidated": 0}
    try:
        provider = get_push_provider()
    except Exception:
        for attempt in attempts:
            attempt.status = "retryable"
            attempt.provider_reason = "ProviderUnavailable"
            attempt.next_attempt_at = now + timedelta(seconds=30)
        db.commit()
        counts["retryable"] = len(attempts)
        return counts
    for attempt in attempts:
        notification = db.get(Notification, attempt.notification_id)
        device = db.get(PushDevice, attempt.device_id)
        if notification is None or device is None or not device.active:
            attempt.status = "cancelled"
            continue
        attempt.attempt_count += 1
        attempt.attempted_at = now
        attempt.status = "delivering"
        counts["processed"] += 1
        try:
            token = decrypt_device_token(device)
            result = provider.send(token, apns_payload(notification))
            attempt.provider_status = result.status_code
            attempt.provider_reason = (result.reason or "")[:128] or None
            attempt.provider_message_id = (result.message_id or "")[:128] or None
            if result.delivered:
                attempt.status = "delivered"
                notification.delivered_at = now
                counts["delivered"] += 1
            elif result.invalid_token:
                attempt.status = "invalidated"
                device.active = False
                counts["invalidated"] += 1
            else:
                attempt.status = "failed" if attempt.attempt_count >= 5 else "retryable"
                counts["retryable"] += int(attempt.status == "retryable")
        except Exception:  # provider boundary: business data is already committed
            attempt.status = "failed" if attempt.attempt_count >= 5 else "retryable"
            attempt.provider_reason = "ProviderUnavailable"
            counts["retryable"] += int(attempt.status == "retryable")
        if attempt.status == "retryable":
            delay_seconds = min(30 * (2 ** (attempt.attempt_count - 1)), 3_600)
            attempt.next_attempt_at = now + timedelta(seconds=delay_seconds)
    db.commit()
    return counts


@event.listens_for(Session, "after_commit")
def _schedule_committed_push_outbox(session: Session) -> None:
    if not session.info.pop("push_outbox_pending", False):
        return
    settings = get_settings()
    if settings.push_mode == "fake":
        # Fake mode has no external dependency and closes the local/test loop
        # deterministically. It still runs in a new post-commit transaction.
        from onemore.core.database import SessionLocal

        try:
            with SessionLocal() as delivery_db:
                drain_push_outbox(delivery_db)
        except Exception:
            # No provider-side failure may change the committed business result.
            return
        return
    try:
        from onemore.tasks.celery_app import celery_app

        celery_app.send_task("onemore.notify.deliver_outbox")
    except Exception:
        # The durable row remains pending; beat/another worker will recover it.
        return


def notification_preferences(user: User) -> dict:
    categories = {**DEFAULT_NOTIFICATION_PREFERENCES, **(user.notification_preferences or {})}
    return {
        "overall_enabled": user.notification_enabled,
        "calendar_sync_enabled": user.calendar_enabled,
        "categories": categories,
        "system_settings_managed_locally": SYSTEM_SETTINGS_MANAGED_LOCALLY,
    }


def update_notification_preferences(
    db: Session, user: User, patch: NotificationPreferencesPatch
) -> dict:
    previous_calendar_enabled = user.calendar_enabled
    if patch.overall_enabled is not None:
        user.notification_enabled = patch.overall_enabled
    if patch.calendar_sync_enabled is not None:
        user.calendar_enabled = patch.calendar_sync_enabled
    if patch.categories is not None:
        user.notification_preferences = {
            **DEFAULT_NOTIFICATION_PREFERENCES,
            **(user.notification_preferences or {}),
            **patch.categories.model_dump(exclude_none=True),
        }
    if (
        patch.calendar_sync_enabled is not None
        and patch.calendar_sync_enabled != previous_calendar_enabled
    ):
        _enqueue_calendar_preference_reconciliation(
            db, user.id, enabled=patch.calendar_sync_enabled
        )
    db.commit()
    db.refresh(user)
    return notification_preferences(user)


def _calendar_event_payload(gathering: Gathering, member_count: int) -> dict:
    return {
        "title": gathering.title,
        "start_at": gathering.start_at.isoformat() if gathering.start_at else None,
        "end_at": gathering.end_at.isoformat() if gathering.end_at else None,
        "location": gathering.location,
        "member_count": member_count,
    }


def _enqueue_calendar_preference_reconciliation(
    db: Session, user_id: str, *, enabled: bool
) -> None:
    now = datetime.now(UTC)
    gatherings = list(
        db.scalars(
            select(Gathering)
            .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
            .where(
                GatheringMember.user_id == user_id,
                GatheringMember.left_at.is_(None),
                Gathering.status.in_(
                    [GatheringStatus.EXECUTED.value, GatheringStatus.ACTIVE.value]
                ),
                Gathering.end_at.is_not(None),
                Gathering.end_at > now,
            )
        )
    )
    for gathering in gatherings:
        if enabled:
            member_count = len(
                list(
                    db.scalars(
                        select(GatheringMember.id).where(
                            GatheringMember.gathering_id == gathering.id,
                            GatheringMember.left_at.is_(None),
                        )
                    )
                )
            )
            push(
                db,
                user_id,
                "execution_succeeded",
                {
                    "gathering_id": gathering.id,
                    "deep_link": f"onemore://gathering/{gathering.id}/space",
                    "calendar_event": _calendar_event_payload(
                        gathering, member_count
                    ),
                    "summary": "日历自动同步已开启，准备同步本局安排",
                },
                dedupe_key=f"calendar-setting-enable:{gathering.id}:{user_id}",
            )
        else:
            push(
                db,
                user_id,
                "calendar_revoked",
                {
                    "gathering_id": gathering.id,
                    "remove_event": True,
                    "summary": "日历自动同步已关闭",
                },
                dedupe_key=f"calendar-setting-disable:{gathering.id}:{user_id}",
            )


def push_delivery_enabled(user: User, notification_type: str) -> bool:
    category_by_type = {
        "chat_message": "chat_messages",
        "trust_level_changed": "trust_updates",
        "competition_deadline": "competition_deadlines",
        "execution_succeeded": "action_updates",
        "authorization_required": "action_updates",
        "reauthorization_required": "action_updates",
        "relation_ready": "gathering_updates",
    }
    category = category_by_type.get(notification_type, "gathering_updates")
    categories = {**DEFAULT_NOTIFICATION_PREFERENCES, **(user.notification_preferences or {})}
    return user.notification_enabled and categories.get(category, True)


def notify_confirmation_required(db: Session, gathering: Gathering) -> list[Notification]:
    deadline = (
        ensure_utc(gathering.confirmation_deadline).isoformat()
        if gathering.confirmation_deadline
        else "current"
    )
    notifications: list[Notification] = []
    for member in list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.left_at.is_(None),
            )
        )
    ):
        notifications.append(
            push(
                db,
                member.user_id,
                "confirmation_required",
                {
                    "gathering_id": gathering.id,
                    "screen_id": "E3",
                    "deep_link": f"onemore://gathering/{gathering.id}/confirm",
                    "summary": "组局已凑齐，请分别确认参加",
                },
                dedupe_key=f"confirmation:{gathering.id}:{deadline}",
            )
        )
    return notifications


def notify_authorization_required(
    db: Session, gathering_id: str, action_id: str
) -> list[Notification]:
    notifications: list[Notification] = []
    for member in list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
    ):
        notifications.append(
            push(
                db,
                member.user_id,
                "authorization_required",
                {
                    "gathering_id": gathering_id,
                    "action_id": action_id,
                    "screen_id": "E5",
                    "deep_link": f"onemore://gathering/{gathering_id}/action",
                    "summary": "行动预览已生成，请核对参数与授权状态",
                },
                dedupe_key=f"authorization:{action_id}",
            )
        )
    return notifications


def notify_reauthorization_required(
    db: Session,
    user_id: str,
    *,
    action_id: str | None = None,
    gathering_id: str | None = None,
) -> Notification:
    payload = {
        "screen_id": "G3",
        "deep_link": "onemore://auth/reauthorize",
        "summary": "校园授权会话已失效，请重新扫码后继续原操作",
    }
    if action_id:
        payload["action_id"] = action_id
    if gathering_id:
        payload["gathering_id"] = gathering_id
    return push(
        db,
        user_id,
        "reauthorization_required",
        payload,
        dedupe_key=f"reauthorize:{action_id or gathering_id or user_id}",
    )


def notify_completion_confirmation(
    db: Session, gathering: Gathering
) -> list[Notification]:
    notifications: list[Notification] = []
    for member in list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.left_at.is_(None),
                GatheringMember.completion_confirmed.is_(False),
            )
        )
    ):
        if db.scalar(
            select(TrustEvent.id).where(
                TrustEvent.user_id == member.user_id,
                TrustEvent.reference_id == gathering.id,
                TrustEvent.event_type.in_(
                    ["completion_confirmed", "no_show", "completion_unresolved"]
                ),
            )
        ):
            continue
        notifications.append(
            push(
                db,
                member.user_id,
                "completion_confirmation",
                {
                    "gathering_id": gathering.id,
                    "deep_link": f"onemore://gathering/{gathering.id}/result",
                    "summary": "本次组局已到结束时间，请确认是否完成",
                },
                dedupe_key=f"completion:{gathering.id}:{member.user_id}",
            )
        )
    return notifications


def notify_relation_ready(
    db: Session, relation_id: str, user_ids: tuple[str, str]
) -> list[Notification]:
    return [
        push(
            db,
            user_id,
            "relation_ready",
            {
                "relation_id": relation_id,
                "screen_id": "E16",
                "deep_link": f"onemore://relation/{relation_id}",
                "summary": "共同完成已沉淀为搭子关系",
            },
            dedupe_key=f"relation-ready:{relation_id}",
        )
        for user_id in user_ids
    ]


def push(
    db: Session,
    user_id: str,
    notification_type: str,
    payload: dict,
    *,
    dedupe_key: str | None = None,
) -> Notification:
    if notification_type not in ALLOWED_NOTIFICATION_TYPES:
        raise AppError("NOTIFICATION_TYPE_NOT_ALLOWED", "通知类型不在允许清单内", 500)
    user = db.get(User, user_id)
    if user is not None and not push_delivery_enabled(user, notification_type):
        payload = {**payload, "push_delivery_suppressed": True}
    if dedupe_key:
        existing = db.scalar(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.type == notification_type,
                Notification.dedupe_key == dedupe_key,
            )
        )
        if existing:
            return existing
    if notification_type == "chat_message" and payload.get("channel_id"):
        cutoff = datetime.now(UTC) - timedelta(minutes=5)
        existing = db.scalar(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.type == "chat_message",
                Notification.created_at >= cutoff,
            )
            .order_by(Notification.created_at.desc())
        )
        if existing and existing.payload.get("channel_id") == payload["channel_id"]:
            existing.payload = {
                "channel_id": payload["channel_id"],
                "deep_link": payload.get("deep_link"),
                "summary": "会话有新消息",
                "grouped": True,
            }
            db.flush()
            _enqueue_notification_delivery(db, existing)
            return existing
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        payload=payload,
        dedupe_key=dedupe_key,
    )
    db.add(notification)
    db.flush()
    _enqueue_notification_delivery(db, notification)
    return notification


def sync_calendar(db: Session, gathering_id: str) -> list[Notification]:
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    if gathering.status != GatheringStatus.EXECUTED.value:
        raise ConflictError("CALENDAR_NOT_READY", "只有执行成功后才生成日历事件")
    members = list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
    )
    created: list[Notification] = []
    for member in members:
        user = db.get(User, member.user_id)
        payload: dict[str, Any] = {
            "gathering_id": gathering.id,
            "deep_link": f"onemore://gathering/{gathering.id}/space",
            "summary": "校园行动已执行成功",
        }
        if user is not None and user.calendar_enabled:
            payload["calendar_event"] = _calendar_event_payload(
                gathering, len(members)
            )
        created.append(
            push(
                db,
                member.user_id,
                "execution_succeeded",
                payload,
                dedupe_key=f"execution:{gathering.id}",
            )
        )
    return created


def revoke_calendar(db: Session, gathering_id: str) -> list[Notification]:
    members = list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
    )
    return [
        push(
            db,
            member.user_id,
            "calendar_revoked",
            {"gathering_id": gathering_id, "remove_event": True},
        )
        for member in members
    ]


def register_device(db: Session, user_id: str, token: str, platform: str) -> PushDevice:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    token_ciphertext, token_key_id = encrypt_device_token(token)
    # An APNs token identifies one physical app installation. A global unique
    # index guarantees that concurrent account switches can never leave two
    # active owners. The existing row is transferred instead of copied.
    device = db.scalar(select(PushDevice).where(PushDevice.token_hash == token_hash))
    if device is None:
        device = PushDevice(
            user_id=user_id,
            token_hash=token_hash,
            token_ciphertext=token_ciphertext,
            token_key_id=token_key_id,
            platform=platform,
        )
        db.add(device)
    else:
        device.user_id = user_id
        device.platform = platform
        device.token_ciphertext = token_ciphertext
        device.token_key_id = token_key_id
    device.active = True
    try:
        db.commit()
    except IntegrityError:
        # A concurrent insert won the global unique index. Re-read and transfer
        # that canonical row; no duplicate token row can be committed.
        db.rollback()
        device = db.scalar(select(PushDevice).where(PushDevice.token_hash == token_hash))
        if device is None:
            raise
        device.user_id = user_id
        device.platform = platform
        device.token_ciphertext = token_ciphertext
        device.token_key_id = token_key_id
        device.active = True
        db.commit()
    db.refresh(device)
    return device


def device_deactivation_token(user_id: str, token_hash: str) -> str:
    payload = f"v1:{user_id}:{token_hash}".encode()
    signature = hmac.new(
        get_settings().auth_signing_key.encode(),
        b"push-device-deactivate:" + payload,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(payload + b"." + signature).rstrip(b"=").decode()


def _verify_device_deactivation_token(value: str) -> tuple[str, str] | None:
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded.encode())
        payload, supplied = raw.rsplit(b".", 1)
        expected = hmac.new(
            get_settings().auth_signing_key.encode(),
            b"push-device-deactivate:" + payload,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(supplied, expected):
            return None
        version, user_id, token_hash = payload.decode().split(":", 2)
        if version != "v1" or len(token_hash) != 64:
            return None
        return user_id, token_hash
    except (ValueError, UnicodeDecodeError):
        return None


def deactivate_installation(db: Session, token: str, proof: str) -> int:
    verified = _verify_device_deactivation_token(proof)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if verified is None or verified[1] != token_hash:
        raise AppError("DEVICE_DEACTIVATION_INVALID", "设备注销凭证无效或已失效", 403)
    user_id, _ = verified
    # Ownership is checked at use time. A proof issued to account A cannot
    # deactivate the same APNs token after it has been transferred to B.
    device = db.scalar(
        select(PushDevice).where(
            PushDevice.token_hash == token_hash,
            PushDevice.user_id == user_id,
            PushDevice.active.is_(True),
        )
    )
    if device is None:
        return 0
    device.active = False
    db.commit()
    return 1


def deactivate_device(db: Session, user_id: str, token: str) -> int:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    device_ids = list(
        db.scalars(
            select(PushDevice.id).where(
                PushDevice.user_id == user_id,
                PushDevice.token_hash == token_hash,
                PushDevice.active.is_(True),
            )
        )
    )
    db.execute(
        update(PushDevice)
        .where(
            PushDevice.user_id == user_id,
            PushDevice.token_hash == token_hash,
            PushDevice.active.is_(True),
        )
        .values(active=False)
    )
    db.commit()
    return len(device_ids)


def list_notifications(db: Session, user_id: str, limit: int = 50) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
    )


def schedule_gathering_reminders(db: Session) -> int:
    now = datetime.now(UTC)
    sent = 0
    for delta, label in ((timedelta(hours=24), "T-24h"), (timedelta(hours=2), "T-2h")):
        lower = now + delta - timedelta(minutes=5)
        upper = now + delta + timedelta(minutes=5)
        gatherings = list(
            db.scalars(
                select(Gathering).where(
                    Gathering.status.in_(
                        [GatheringStatus.EXECUTED.value, GatheringStatus.ACTIVE.value]
                    ),
                    Gathering.start_at >= lower,
                    Gathering.start_at < upper,
                )
            )
        )
        for gathering in gatherings:
            for member in db.scalars(
                select(GatheringMember).where(
                    GatheringMember.gathering_id == gathering.id,
                    GatheringMember.left_at.is_(None),
                )
            ):
                push(
                    db,
                    member.user_id,
                    "gathering_reminder",
                    {
                        "gathering_id": gathering.id,
                        "label": label,
                        "deep_link": f"onemore://gathering/{gathering.id}/space",
                    },
                    dedupe_key=f"reminder:{gathering.id}:{label}",
                )
                sent += 1
    db.commit()
    return sent
