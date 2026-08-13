from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.contact_policy import users_have_block_between
from onemore.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from onemore.core.locks import gathering_locks, user_locks
from onemore.core.time import ensure_utc
from onemore.db.models import (
    ActionModification,
    ActionStatus,
    AuthorizationGrant,
    CampusAction,
    Channel,
    ChannelStatus,
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    GatheringRecurrenceDecision,
    GatheringStatus,
    GatheringTransition,
    IntentCard,
    IntentStatus,
    OrganizerAttendance,
    Report,
    RescheduleProposal,
    RescheduleVote,
    TrustEvent,
    TrustLevel,
    User,
    UserBlock,
    new_id,
    utcnow,
)
from onemore.hermes.schemas import ActionName, GymBookParams, RoomReserveParams
from onemore.modules.gathering.schemas import (
    InitiateGatheringRequest,
    RecurringGatheringRequest,
)
from onemore.modules.gathering.state_machine import GatheringEvent, transition
from onemore.modules.schedule import service as schedule_service
from onemore.modules.trust import service as trust_service
from onemore.modules.trust.service import LEVEL_ORDER

IDENTITY_VISIBLE_STATES = {
    GatheringStatus.CONFIRMED.value,
    GatheringStatus.PREVIEWED.value,
    GatheringStatus.EXECUTED.value,
    GatheringStatus.ACTIVE.value,
    GatheringStatus.COMPLETED.value,
    GatheringStatus.RECURRENCE_PENDING.value,
    GatheringStatus.ARCHIVED.value,
}

TERMINAL_GATHERING_STATES = {
    GatheringStatus.COMPLETED.value,
    GatheringStatus.RECURRENCE_PENDING.value,
    GatheringStatus.ARCHIVED.value,
    GatheringStatus.DISSOLVED.value,
}


def is_expired(gathering: Gathering, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    return bool(
        (
            gathering.expires_at is not None
            and ensure_utc(gathering.expires_at) <= current
        )
        or (
            gathering.end_at is not None
            and ensure_utc(gathering.end_at) <= current
        )
    )


def _finalize_expired_locked(db: Session, gathering: Gathering) -> None:
    if gathering.status != GatheringStatus.POOLING.value or not is_expired(gathering):
        return
    members = active_members(db, gathering.id)
    member_ids = [member.user_id for member in members]
    if gathering.is_official and len(members) >= gathering.min_size:
        transition(db, gathering, GatheringEvent.MATCHED)
        from onemore.modules.notify.service import notify_confirmation_required

        notify_confirmation_required(db, gathering)
        return
    transition(db, gathering, GatheringEvent.DISSOLVE)
    if gathering.source_intent_id:
        intent = db.get(IntentCard, gathering.source_intent_id)
        if intent is not None and intent.status == IntentStatus.POOLING.value:
            intent.status = IntentStatus.EXPIRED.value
    from onemore.modules.notify.service import push

    for member_id in member_ids:
        push(
            db,
            member_id,
            "silent_dissolution",
            {
                "gathering_id": gathering.id,
                "deep_link": "onemore://my-gatherings",
                "summary": "本次招募到期未成局，已安静收起",
            },
            dedupe_key=f"dissolved:{gathering.id}",
        )
    db.execute(
        delete(GatheringMember).where(GatheringMember.gathering_id == gathering.id)
    )


def _share_signature(payload: str) -> str:
    key = get_settings().auth_signing_key.encode()
    digest = hmac.new(key, f"gap-share:{payload}".encode(), hashlib.sha256).digest()[:18]
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue_gap_share_token(gathering_id: str) -> str:
    payload = base64.urlsafe_b64encode(gathering_id.encode()).decode().rstrip("=")
    return f"v1.{payload}.{_share_signature(payload)}"


def resolve_gap_share_token(token: str) -> str:
    try:
        version, payload, signature = token.split(".", 2)
        if version != "v1" or not hmac.compare_digest(signature, _share_signature(payload)):
            raise ValueError
        padded = payload + "=" * ((4 - len(payload) % 4) % 4)
        gathering_id = base64.urlsafe_b64decode(padded.encode()).decode()
        if not gathering_id or len(gathering_id) > 128:
            raise ValueError
        return gathering_id
    except (UnicodeDecodeError, ValueError, TypeError):
        # Invalid and unknown tokens intentionally share the same response.
        raise NotFoundError("分享链接", "invalid") from None


def _gathering_mood_note(db: Session, gathering: Gathering) -> str | None:
    if gathering.source_intent_id is None:
        return None
    intent = db.get(IntentCard, gathering.source_intent_id)
    return intent.mood_note if intent is not None else None


def gap_share_view(db: Session, token: str) -> dict:
    gathering = get_gathering(db, resolve_gap_share_token(token))
    now = datetime.now(UTC)
    joinable = gathering.status == GatheringStatus.POOLING.value and (
        gathering.expires_at is None or ensure_utc(gathering.expires_at) > now
    )
    base = get_settings().public_web_base_url.rstrip("/")
    # 缺口是唯一对外的数字：它是产品的社交符号（“还差一个”），
    # 不暴露身份、名单或报名明细。
    missing_count = (
        max(gathering.target_size - len(active_members(db, gathering.id)), 0)
        if joinable
        else 0
    )
    return {
        "share_token": token,
        "gathering_id": gathering.id,
        "gathering_type": gathering.gathering_type,
        "title": gathering.title,
        "goal": gathering.goal,
        "mood_note": _gathering_mood_note(db, gathering),
        "status": gathering.status,
        "campus": gathering.campus,
        "start_at": gathering.start_at,
        "end_at": gathering.end_at,
        "target_size": gathering.target_size,
        "missing_count": missing_count,
        "expires_at": gathering.expires_at,
        "joinable": joinable,
        "deep_link": f"onemore://g/{token}",
        "universal_link": f"{base}/g/{token}",
        "looking_for": _looking_for_labels(
            db,
            _remaining_required_roles(gathering, active_members(db, gathering.id)),
        ),
    }


def create_gap_share(db: Session, gathering_id: str, user_id: str) -> dict:
    with gathering_locks.acquire(gathering_id):
        db.expire_all()
        gathering = get_gathering(db, gathering_id)
        require_member(db, gathering_id, user_id)
        if is_expired(gathering):
            _finalize_expired_locked(db, gathering)
            db.commit()
            raise AppError("GATHERING_EXPIRED", "本局招募已到期", 410)
        if gathering.status != GatheringStatus.POOLING.value:
            raise ConflictError("GATHERING_NOT_SHAREABLE", "只有正在匿名招募的局可生成缺口卡")
        return gap_share_view(db, issue_gap_share_token(gathering.id))


def _pending_action_modification(db: Session, gathering_id: str) -> dict | None:
    row = db.execute(
        select(ActionModification, CampusAction)
        .join(CampusAction, CampusAction.id == ActionModification.action_id)
        .where(
            CampusAction.gathering_id == gathering_id,
            ActionModification.status == "requested",
        )
        .order_by(ActionModification.created_at.desc())
    ).first()
    if row is None:
        return None
    modification, action = row
    return {
        "action_id": action.id,
        "reason": modification.reason,
        "proposed_params": modification.proposed_params,
        "created_at": modification.created_at,
    }


def _disabled_action(reason: str, pending_modification: dict | None = None) -> dict:
    return {
        "enabled": False,
        "action": None,
        "params": {},
        "disabled_reason": reason,
        "pending_modification": pending_modification,
    }


def _room_codes(location: str) -> tuple[str, str] | None:
    # Locations eligible for agent booking must carry both the server-known
    # room type and room identifier, e.g. “图书馆研讨室 15-401”.
    match = re.search(r"(?:研讨室|房间|room)\s*([A-Za-z0-9]{1,8})[-/]([A-Za-z0-9_-]{1,32})", location, re.I)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _gym_codes(location: str) -> tuple[str, str | None] | None:
    # A selected option is persisted in a human-readable but unambiguous form.
    match = re.search(r"(?:体育场馆|gym)\s*\[([^\]]{1,100})\](?:\s+(.{1,100}))?", location, re.I)
    if match is None:
        return None
    venue = match.group(2).strip() if match.group(2) else None
    return match.group(1), venue


def _booking_signature(payload: str) -> str:
    key = get_settings().auth_signing_key.encode()
    digest = hmac.new(
        key, f"gathering-booking-option:{payload}".encode(), hashlib.sha256
    ).digest()[:18]
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _issue_booking_option(payload: dict) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    return f"v1.{encoded}.{_booking_signature(encoded)}"


def _resolve_booking_option(token: str) -> dict:
    try:
        version, payload, signature = token.split(".", 2)
        if version != "v1" or not hmac.compare_digest(signature, _booking_signature(payload)):
            raise ValueError
        padded = payload + "=" * ((4 - len(payload) % 4) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if not isinstance(value, dict) or int(value["exp"]) < int(datetime.now(UTC).timestamp()):
            raise ValueError
        required = {"g", "resource_type", "action", "kind", "date", "start", "end", "location"}
        if not required <= value.keys():
            raise ValueError
        return value
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise AppError("BOOKING_OPTION_INVALID", "预约选项已失效，请重新查询", 409) from None


def _slot_covers(slot: dict, start: str, end: str) -> bool:
    if slot.get("available") is False or slot.get("full") is True:
        return False
    slot_start = slot.get("start") or slot.get("start_time")
    slot_end = slot.get("end") or slot.get("end_time")
    if not isinstance(slot_start, str) or not isinstance(slot_end, str):
        return False
    return slot_start[:5] <= start and slot_end[:5] >= end


def booking_options(db: Session, gathering_id: str, user_id: str) -> list[dict]:
    """Return only options verified by a fresh read through the Hermes boundary."""

    gathering = get_gathering(db, gathering_id)
    require_member(db, gathering_id, user_id)
    if gathering.owner_user_id != user_id:
        raise ForbiddenError("只有本局发起人可以选择预约方案")
    if gathering.status != GatheringStatus.CONFIRMED.value:
        raise ConflictError("GATHERING_NOT_CONFIRMED", "全体成员确认后才可查询预约方案")
    if gathering.start_at is None or gathering.end_at is None:
        raise ConflictError("GATHERING_TIME_MISSING", "服务端尚未确定本局时间")

    from onemore.modules.actions import service as action_service

    timezone = ZoneInfo("Asia/Shanghai")
    start = ensure_utc(gathering.start_at).astimezone(timezone)
    end = ensure_utc(gathering.end_at).astimezone(timezone)
    if start.date() != end.date():
        raise ConflictError("BOOKING_WINDOW_CROSSES_DAY", "跨日时段暂不支持校园预约")
    start_text, end_text = start.strftime("%H:%M"), end.strftime("%H:%M")
    expires = int((datetime.now(UTC) + timedelta(minutes=10)).timestamp())
    values: list[dict] = []

    if any(keyword in gathering.gathering_type for keyword in ("运动", "羽毛球", "篮球", "足球", "网球", "健身")):
        venue_type = "badminton" if "羽毛球" in gathering.goal or "羽毛球" in gathering.title else "sports"
        result = action_service.execute_read_action(
            db,
            user_id,
            ActionName.GYM_AVAILABLE,
            {
                "venue_type": venue_type,
                "date": start.date(),
                "days": 1,
                "venue": None,
                "include_full": False,
            },
        )
        slots = result.get("slots", []) if isinstance(result, dict) else []
        for slot in slots if isinstance(slots, list) else []:
            if not isinstance(slot, dict) or not _slot_covers(slot, start_text, end_text):
                continue
            kind = str(slot.get("venue_type") or venue_type)
            venue_raw = slot.get("venue") or slot.get("name")
            venue = str(venue_raw) if venue_raw else None
            location = f"体育场馆 [{kind}]" + (f" {venue}" if venue else "")
            payload = {
                "g": gathering.id,
                "resource_type": "gym",
                "action": ActionName.GYM_BOOK_PREVIEW.value,
                "kind": kind,
                "resource": venue,
                "date": start.date().isoformat(),
                "start": start_text,
                "end": end_text,
                "location": location,
                "exp": expires,
            }
            values.append(
                {
                    "option_token": _issue_booking_option(payload),
                    "resource_type": "gym",
                    "action": payload["action"],
                    "location": location,
                    "start_at": gathering.start_at,
                    "end_at": gathering.end_at,
                    "label": venue or f"{kind} 场地",
                }
            )
    elif any(keyword in gathering.gathering_type for keyword in ("DDL", "自习", "项目", "研讨", "比赛组队")):
        kind = "15"
        result = action_service.execute_read_action(
            db,
            user_id,
            ActionName.ROOM_AVAILABLE,
            {"kind": kind, "date": start.date(), "lab": None, "room": None},
        )
        slots = result.get("slots", []) if isinstance(result, dict) else []
        for slot in slots if isinstance(slots, list) else []:
            if not isinstance(slot, dict) or not _slot_covers(slot, start_text, end_text):
                continue
            slot_kind = str(slot.get("kind") or kind)
            room_raw = slot.get("room") or slot.get("name")
            if not room_raw:
                continue
            room = str(room_raw)
            location = f"图书馆研讨室 {slot_kind}-{room}"
            payload = {
                "g": gathering.id,
                "resource_type": "room",
                "action": ActionName.ROOM_RESERVE_PREVIEW.value,
                "kind": slot_kind,
                "resource": room,
                "date": start.date().isoformat(),
                "start": start_text,
                "end": end_text,
                "location": location,
                "exp": expires,
            }
            values.append(
                {
                    "option_token": _issue_booking_option(payload),
                    "resource_type": "room",
                    "action": payload["action"],
                    "location": location,
                    "start_at": gathering.start_at,
                    "end_at": gathering.end_at,
                    "label": f"研讨室 {slot_kind}-{room}",
                }
            )
    else:
        raise ConflictError("BOOKING_NOT_SUPPORTED", "此类型的局没有可代理预约的校园资源")
    return values


def select_booking_plan(
    db: Session, gathering_id: str, user_id: str, option_token: str
) -> Gathering:
    selected = _resolve_booking_option(option_token)
    if selected["g"] != gathering_id:
        raise AppError("BOOKING_OPTION_INVALID", "预约选项与当前局不匹配", 409)
    with gathering_locks.acquire(gathering_id):
        db.expire_all()
        current = booking_options(db, gathering_id, user_id)
        match: dict | None = None
        for option in current:
            payload = _resolve_booking_option(option["option_token"])
            fields = ("g", "resource_type", "action", "kind", "resource", "date", "start", "end", "location")
            if all(payload.get(field) == selected.get(field) for field in fields):
                match = payload
                break
        if match is None:
            raise AppError("BOOKING_OPTION_STALE", "该场地已不在实时可预约列表中", 409)
        gathering = get_gathering(db, gathering_id)
        gathering.location = str(match["location"])
        db.commit()
        db.refresh(gathering)
        return gathering


def gathering_action_capability(db: Session, gathering_id: str, user_id: str) -> dict:
    gathering = get_gathering(db, gathering_id)
    require_member(db, gathering_id, user_id)
    pending_modification = _pending_action_modification(db, gathering_id)
    if gathering.owner_user_id != user_id:
        return _disabled_action(
            "等待本局发起人处理行动预览",
            pending_modification,
        )
    if gathering.status not in {
        GatheringStatus.CONFIRMED.value,
        GatheringStatus.PREVIEWED.value,
    }:
        return _disabled_action(
            "全体成员分别确认后才可生成校园写操作预览",
            pending_modification,
        )
    room_supported = any(
        keyword in gathering.gathering_type
        for keyword in ("DDL", "自习", "项目", "研讨", "比赛组队")
    )
    gym_supported = any(
        keyword in gathering.gathering_type
        for keyword in ("运动", "羽毛球", "篮球", "足球", "网球", "健身")
    )
    if not room_supported and not gym_supported:
        return _disabled_action("此类型的局没有可代理执行的校园写操作", pending_modification)
    if gathering.start_at is None or gathering.end_at is None:
        return _disabled_action("服务端尚未确认可预约的开始和结束时间", pending_modification)
    if not gathering.location:
        return _disabled_action("服务端尚未确认可预约的具体地点", pending_modification)
    has_grant = db.scalar(
        select(AuthorizationGrant.granted).where(
            AuthorizationGrant.user_id == user_id,
            AuthorizationGrant.scope == "agent_booking",
        )
    )
    if not has_grant:
        return _disabled_action("需要先开启校园预约代理授权", pending_modification)
    trust = trust_service.ensure_trust_profile(db, user_id)
    if LEVEL_ORDER[trust.level] < LEVEL_ORDER["T2"]:
        return _disabled_action("此操作需要达到 T2 信任等级", pending_modification)

    local_timezone = ZoneInfo("Asia/Shanghai")
    start = ensure_utc(gathering.start_at).astimezone(local_timezone)
    end = ensure_utc(gathering.end_at).astimezone(local_timezone)
    if gym_supported:
        gym_codes = _gym_codes(gathering.location)
        if gym_codes is None:
            return _disabled_action("地点缺少经实时查询确认的体育场馆编号", pending_modification)
        venue_type, venue = gym_codes
        action = ActionName.GYM_BOOK_PREVIEW.value
        params = GymBookParams(
            venue_type=venue_type,
            venue=venue,
            date=start.date(),
            start=start.strftime("%H:%M"),
            end=end.strftime("%H:%M"),
        ).model_dump(mode="json")
    else:
        room_codes = _room_codes(gathering.location)
        if room_codes is None:
            return _disabled_action("地点缺少经实时查询确认的场地类型与房间编号", pending_modification)
        kind, room = room_codes
        members = [
            item.user_id
            for item in active_members(db, gathering_id)
            if item.user_id != user_id
        ]
        action = ActionName.ROOM_RESERVE_PREVIEW.value
        params = RoomReserveParams(
            kind=kind,
            room=room,
            date=start.date(),
            start=start.strftime("%H:%M"),
            end=end.strftime("%H:%M"),
            members=members,
            title=gathering.title[:80],
            memo=gathering.goal[:200],
            services=[],
        ).model_dump(mode="json")
    return {
        "enabled": True,
        "action": action,
        "params": params,
        "disabled_reason": None,
        "pending_modification": pending_modification,
    }


def get_gathering(db: Session, gathering_id: str) -> Gathering:
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    return gathering


def get_gathering_for_viewer(
    db: Session, gathering_id: str, user_id: str
) -> Gathering:
    """Return only a gathering the viewer can legitimately discover.

    Member-only states contain exact meeting time and location.  Knowing a
    UUID (including one learned from a formerly valid share card) must not
    turn those details into a public lookup endpoint.
    """

    gathering = get_gathering(db, gathering_id)
    member = db.scalar(
        select(GatheringMember.id).where(
            GatheringMember.gathering_id == gathering.id,
            GatheringMember.user_id == user_id,
            GatheringMember.left_at.is_(None),
        )
    )
    if member is not None:
        now = datetime.now(UTC)
        if (
            gathering.status
            in {
                GatheringStatus.CONFIRMED.value,
                GatheringStatus.PREVIEWED.value,
                GatheringStatus.EXECUTED.value,
            }
            and gathering.start_at is not None
            and ensure_utc(gathering.start_at) <= now
        ):
            transition(db, gathering, GatheringEvent.START)
            db.commit()
            db.refresh(gathering)
        return gathering
    if gathering.status != GatheringStatus.POOLING.value or is_expired(gathering):
        raise NotFoundError("局", gathering_id)
    if _backfill_window(gathering) is not None and _matching_backfill_intent(
        db, gathering, user_id
    ) is None:
        raise NotFoundError("局", gathering_id)
    return gathering


def active_members(db: Session, gathering_id: str) -> list[GatheringMember]:
    return list(
        db.scalars(
            select(GatheringMember)
            .where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
            .order_by(GatheringMember.created_at)
        )
    )


def require_member(db: Session, gathering_id: str, user_id: str) -> GatheringMember:
    member = db.scalar(
        select(GatheringMember).where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.user_id == user_id,
            GatheringMember.left_at.is_(None),
        )
    )
    if member is None:
        raise ForbiddenError("只有局成员可执行此操作")
    return member


def _channel_id(db: Session, gathering_id: str) -> str | None:
    return db.scalar(select(Channel.id).where(Channel.gathering_id == gathering_id))


def _action_id(db: Session, gathering_id: str) -> str | None:
    return db.scalar(
        select(CampusAction.id)
        .where(
            CampusAction.gathering_id == gathering_id,
            CampusAction.status.in_(
                [
                    ActionStatus.PREVIEWED.value,
                    ActionStatus.EXECUTING.value,
                    ActionStatus.SUCCEEDED.value,
                    ActionStatus.FAILED.value,
                ]
            ),
        )
        .order_by(CampusAction.updated_at.desc())
    )


_ROLE_LABELS = {
    "frontend": "前端",
    "backend": "后端",
    "design": "设计",
    "visual_design": "视觉",
    "product": "产品",
    "data_analysis": "数据分析",
    "machine_learning": "机器学习",
    "algorithm": "算法",
    "presentation": "路演",
    "writing": "文案",
    "paper_writing": "写作",
    "research": "调研",
    "video": "视频",
    "operations": "运营",
    "business_analysis": "商业分析",
    "modeling": "建模",
    "programming": "编程",
}
_ROLE_KEYS_BY_LABEL = {label: key for key, label in _ROLE_LABELS.items()}


def _normalize_role_key(role: str | None) -> str:
    raw = (role or "").strip()
    if not raw:
        return ""
    if raw in _ROLE_LABELS:
        return raw
    return _ROLE_KEYS_BY_LABEL.get(raw, raw)


def _remaining_required_roles(
    gathering: Gathering, members: list[GatheringMember]
) -> list[str]:
    """Roles still advertised as gaps, matching Chinese or English member roles."""
    required = [
        key
        for item in (gathering.required_roles or [])
        if (key := _normalize_role_key(item))
    ]
    bag = [
        key
        for item in members
        if (key := _normalize_role_key(item.role))
    ]
    remaining: list[str] = []
    for role in required:
        if role in bag:
            bag.remove(role)
        else:
            remaining.append(role)
    return remaining


def _looking_for_labels(db: Session, role_keys: list[str]) -> list[str]:
    """Identity-free recruit copy: capability labels the table still needs."""
    if not role_keys:
        return []
    from onemore.db.models import CapabilityTag

    rows = {
        row.key: row.label
        for row in db.scalars(select(CapabilityTag).where(CapabilityTag.key.in_(role_keys)))
    }
    labels: list[str] = []
    for key in role_keys:
        mapped = _ROLE_LABELS.get(key)
        label = rows.get(key) or mapped or key
        if label.startswith("taste:"):
            continue
        if mapped and label.isascii():
            label = mapped
        if label and label not in labels:
            labels.append(label)
    return labels[:6]


def _filled_role_labels(db: Session, members: list[GatheringMember]) -> list[str]:
    ordered = sorted(
        members,
        key=lambda item: (0 if item.joined_via == "owner" else 1, item.id),
    )
    return _looking_for_labels(
        db,
        [item.role for item in ordered if (item.role or "").strip()],
    )


def _roster_highlights(db: Session, gathering: Gathering, members: list[GatheringMember]) -> list[str]:
    """Anonymous table flavor: experience and mode, never names or colleges."""
    from onemore.db.models import TrustProfile

    highlights: list[str] = []
    trust = db.get(TrustProfile, gathering.owner_user_id)
    if trust is not None:
        completed = int(trust.completed_gatherings or 0)
        initiated = int(trust.initiated_gatherings or 0)
        if trust.level in {TrustLevel.T3.value, TrustLevel.T4.value} or completed >= 6:
            highlights.append("高手带队")
        elif completed >= 3 or initiated >= 1:
            highlights.append("有人带过队")
        if completed >= 3 and float(trust.on_time_confirm_rate or 0) >= 0.95:
            highlights.append("到场稳")
    if gathering.mode == "complementary":
        highlights.append("按角色互补")
    seen: list[str] = []
    for item in highlights:
        if item not in seen:
            seen.append(item)
    return seen[:3]


def to_view(db: Session, gathering: Gathering, viewer_id: str | None) -> dict:
    members = active_members(db, gathering.id)
    member = next((item for item in members if item.user_id == viewer_id), None)
    visible_counts = gathering.status != GatheringStatus.POOLING.value
    identity_threshold_satisfied = (
        gathering.status in IDENTITY_VISIBLE_STATES
        or gathering.identity_disclosure == "after_confirmed"
        or len(members) >= gathering.target_size
    )
    identity_visible = (
        gathering.status in IDENTITY_VISIBLE_STATES
        and member is not None
        and identity_threshold_satisfied
    )
    participants = None
    if identity_visible:
        from onemore.db.models import TasteProfile
        from onemore.modules.taste_profile.service import public_interest_tags

        participants = []
        for item in members:
            user = db.get(User, item.user_id)
            taste = db.get(TasteProfile, item.user_id)
            participants.append(
                {
                    "user_id": item.user_id,
                    "display_name": user.display_name if user else None,
                    "college": user.college if user else None,
                    "major": user.major if user else None,
                    "role": item.role,
                    "interest_tags": public_interest_tags(db, item.user_id),
                    "taste_summary": (taste.summary if taste else None) or None,
                }
            )
    reportable_participants = (
        _reportable_participants(db, gathering, viewer_id)
        if viewer_id is not None
        else []
    )
    recurrence_decision = (
        db.scalar(
            select(GatheringRecurrenceDecision).where(
                GatheringRecurrenceDecision.gathering_id == gathering.id,
                GatheringRecurrenceDecision.user_id == viewer_id,
            )
        )
        if viewer_id is not None
        else None
    )
    return {
        "id": gathering.id,
        "title": gathering.title,
        "goal": gathering.goal,
        "mood_note": _gathering_mood_note(db, gathering),
        "gathering_type": gathering.gathering_type,
        "mode": gathering.mode,
        "status": gathering.status,
        "campus": gathering.campus,
        "same_gender_only": gathering.same_gender_only,
        "identity_disclosure": gathering.identity_disclosure,
        "start_at": gathering.start_at,
        "end_at": gathering.end_at,
        "location": gathering.location,
        "min_size": gathering.min_size,
        "target_size": gathering.target_size,
        "required_trust_level": gathering.required_trust_level,
        "required_roles": gathering.required_roles,
        "match_reason": gathering.match_reason if member and visible_counts else None,
        "looking_for": _looking_for_labels(
            db, _remaining_required_roles(gathering, members)
        ),
        "filled_roles": _filled_role_labels(db, members),
        "roster_highlights": (
            _roster_highlights(db, gathering, members)
            if gathering.status == GatheringStatus.POOLING.value
            else []
        ),
        "my_confirmation": member.confirmation_status if member else None,
        "confirmed_count": (
            sum(item.confirmation_status == ConfirmationStatus.CONFIRMED.value for item in members)
            if visible_counts and member
            else None
        ),
        # 产品决策（2026-08-12）：招募期对任何登录用户暴露池内人数（纯计数，
        # 不含身份）；confirmed_count / participants 仍按原门槛隐藏。
        "member_count": (
            len(members)
            if (visible_counts and member)
            or gathering.status == GatheringStatus.POOLING.value
            else None
        ),
        "participants": participants,
        "reportable_participants": reportable_participants,
        "my_recurrence_decision": (
            {
                "decision": recurrence_decision.decision,
                "kept_user_ids": recurrence_decision.kept_user_ids,
                "clone_gathering_id": recurrence_decision.clone_gathering_id,
            }
            if recurrence_decision is not None
            else None
        ),
        "leave_capability": (
            _leave_capability(gathering) if member is not None else None
        ),
        "channel_id": _channel_id(db, gathering.id) if identity_visible else None,
        "action_id": _action_id(db, gathering.id) if member else None,
        "expires_at": gathering.expires_at,
    }


def _reportable_participants(
    db: Session, gathering: Gathering, viewer_id: str
) -> list[dict]:
    """Return only peers whose identity was disclosed while both were present."""

    rows = list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering.id
            )
        )
    )
    viewer = next((row for row in rows if row.user_id == viewer_id), None)
    if viewer is None:
        return []
    disclosure_times = list(
        db.scalars(
            select(GatheringTransition.occurred_at).where(
                GatheringTransition.gathering_id == gathering.id,
                GatheringTransition.to_status.in_(IDENTITY_VISIBLE_STATES),
            )
        )
    )
    if gathering.status in IDENTITY_VISIBLE_STATES:
        disclosure_times.append(utcnow())

    def present_at(row: GatheringMember, occurred_at: datetime) -> bool:
        occurred = ensure_utc(occurred_at)
        return ensure_utc(row.created_at) <= occurred and (
            row.left_at is None or ensure_utc(row.left_at) >= occurred
        )

    result = []
    for row in rows:
        if row.user_id == viewer_id or not any(
            present_at(viewer, occurred_at) and present_at(row, occurred_at)
            for occurred_at in disclosure_times
        ):
            continue
        user = db.get(User, row.user_id)
        result.append(
            {
                "user_id": row.user_id,
                "display_name": user.display_name if user else None,
                "college": user.college if user else None,
                "major": user.major if user else None,
                "role": row.role,
            }
        )
    return result


def list_mine(db: Session, user_id: str) -> list[Gathering]:
    return list(
        db.scalars(
            select(Gathering)
            .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
            .where(GatheringMember.user_id == user_id, GatheringMember.left_at.is_(None))
            .order_by(Gathering.updated_at.desc())
        )
    )


def departed_safety_history(db: Session, user_id: str) -> list[dict]:
    """Return a durable, deliberately limited safety context after departure."""

    rows = list(
        db.scalars(
            select(GatheringMember)
            .where(
                GatheringMember.user_id == user_id,
                GatheringMember.left_at.is_not(None),
            )
            .order_by(GatheringMember.left_at.desc())
            .limit(50)
        )
    )
    result = []
    for row in rows:
        gathering = db.get(Gathering, row.gathering_id)
        if gathering is None or row.left_at is None:
            continue
        result.append(
            {
                "gathering_id": gathering.id,
                "title": gathering.title,
                "gathering_type": gathering.gathering_type,
                "status": gathering.status,
                "left_at": row.left_at,
                "reportable_participants": _reportable_participants(
                    db, gathering, user_id
                ),
            }
        )
    return result


def list_open(
    db: Session,
    *,
    viewer_id: str,
    campus: str | None = None,
    gathering_type: str | None = None,
) -> list[Gathering]:
    now = datetime.now(UTC)
    query = select(Gathering).where(
        Gathering.status == GatheringStatus.POOLING.value,
        or_(Gathering.expires_at.is_(None), Gathering.expires_at > now),
        or_(Gathering.end_at.is_(None), Gathering.end_at > now),
    )
    if campus:
        query = query.where(Gathering.campus == campus)
    if gathering_type:
        query = query.where(Gathering.gathering_type == gathering_type)
    items = list(
        db.scalars(query.order_by(Gathering.is_official.desc(), Gathering.created_at.desc()))
    )
    return [
        item
        for item in items
        if _backfill_window(item) is None
        or _matching_backfill_intent(db, item, viewer_id) is not None
    ]


def initiate(db: Session, user: User, body: InitiateGatheringRequest) -> Gathering:
    """Create a concrete T2-owned gathering without passing through the T1 intent pool."""

    trust_service.require_unlock(db, user.id, "initiate_gathering")
    if not user.social_enabled:
        raise ForbiddenError("请先主动开启社交开关")
    if body.mode == "complementary":
        trust_service.require_unlock(db, user.id, "competition_pool")
    if body.min_size <= 2:
        trust_service.require_unlock(db, user.id, "duo_gathering")
    if body.target_size >= 6:
        trust_service.require_unlock(db, user.id, "large_group")
    if body.cross_college:
        trust_service.require_unlock(db, user.id, "cross_college_matching")
    now = datetime.now(UTC)
    start_at = ensure_utc(body.start_at) if body.start_at else None
    end_at = ensure_utc(body.end_at) if body.end_at else None
    if start_at is not None and start_at <= now:
        raise ConflictError("START_TIME_IN_PAST", "开始时间必须晚于当前时间")
    expires_at = now + timedelta(days=7)
    if start_at is not None:
        expires_at = max(now + timedelta(minutes=5), start_at - timedelta(minutes=30))
    item = Gathering(
        owner_user_id=user.id,
        gathering_type=body.gathering_type,
        mode=body.mode,
        title=body.title,
        goal=body.goal,
        status=GatheringStatus.POOLING.value,
        min_size=body.min_size,
        target_size=body.target_size,
        required_trust_level=(
            TrustLevel.T3.value
            if body.target_size >= 6
            else TrustLevel.T2.value
            if body.mode == "complementary" or body.min_size <= 2 or body.cross_college
            else TrustLevel.T1.value
        ),
        campus=body.campus,
        same_gender_only=user.same_gender_only,
        identity_disclosure=user.identity_disclosure,
        start_at=start_at,
        end_at=end_at,
        location=body.location,
        required_roles=body.required_roles,
        official_metadata={
            "created_via": "self_initiation",
            "cross_college": body.cross_college,
        },
        expires_at=expires_at,
    )
    db.add(item)
    db.flush()
    db.add(
        GatheringMember(
            gathering_id=item.id,
            user_id=user.id,
            joined_via="owner",
        )
    )
    db.commit()
    db.refresh(item)
    return item


def _blocked_with_any(db: Session, user_id: str, members: list[GatheringMember]) -> bool:
    other_ids = [member.user_id for member in members]
    if not other_ids:
        return False
    return (
        db.scalar(
            select(UserBlock.id).where(
                or_(
                    UserBlock.blocker_id == user_id,
                    UserBlock.blocked_id == user_id,
                ),
                or_(
                    UserBlock.blocker_id.in_(other_ids),
                    UserBlock.blocked_id.in_(other_ids),
                ),
            )
        )
        is not None
    )


def _is_competition_team(db: Session, gathering: Gathering) -> bool:
    """赛事组队：人数按 2–3 成局，不占日历时段，满员后直接开群。"""
    metadata = gathering.official_metadata if isinstance(gathering.official_metadata, dict) else {}
    if metadata.get("competition_id") or metadata.get("competition_name"):
        return True
    if "比赛" in (gathering.gathering_type or ""):
        return True
    if gathering.source_intent_id:
        intent = db.get(IntentCard, gathering.source_intent_id)
        if intent is not None and intent.competition_id:
            return True
    return False


def _occupies_timeslot(db: Session, gathering: Gathering) -> bool:
    """Competition teams are not exclusive calendar bookings.

    A math-modeling roster can be joined while the same person already has
    badminton or study at that clock time, and sitting on a competition team
    must not block joining a real timeslot gathering later.
    """
    return not _is_competition_team(db, gathering)


def _competition_roster_ready(
    gathering: Gathering, members: list[GatheringMember]
) -> bool:
    """CUMCM-style teams form at min_size once advertised gaps are gone, or at target."""
    count = len(members)
    if count < gathering.min_size:
        return False
    if count >= gathering.target_size:
        return True
    return not _remaining_required_roles(gathering, members)


def _seal_competition_team(db: Session, gathering: Gathering, actor_user_id: str) -> None:
    now = utcnow()
    for member in active_members(db, gathering.id):
        member.confirmation_status = ConfirmationStatus.CONFIRMED.value
        if member.confirmed_at is None:
            member.confirmed_at = now
    transition(db, gathering, GatheringEvent.ALL_CONFIRMED, actor_user_id=actor_user_id)
    from onemore.modules.collab.service import open_gathering_channel

    open_gathering_channel(db, gathering.id)


def _time_conflict(db: Session, user_id: str, target: Gathering) -> bool:
    if not _occupies_timeslot(db, target):
        return False
    if target.start_at is None or target.end_at is None:
        return False
    overlapping = db.scalars(
        select(Gathering)
        .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
        .where(
            GatheringMember.user_id == user_id,
            GatheringMember.left_at.is_(None),
            Gathering.id != target.id,
            Gathering.status.in_(
                [
                    GatheringStatus.TENTATIVE.value,
                    GatheringStatus.CONFIRMED.value,
                    GatheringStatus.PREVIEWED.value,
                    GatheringStatus.EXECUTED.value,
                    GatheringStatus.ACTIVE.value,
                ]
            ),
            Gathering.start_at < target.end_at,
            Gathering.end_at > target.start_at,
        )
    ).all()
    return any(_occupies_timeslot(db, item) for item in overlapping)


def _join_trust_capability(gathering: Gathering) -> str | None:
    """Name the authoritative capability that made this entry high-commitment."""

    # T4-managed official supply is deliberately available to newly verified
    # students: the organizer owns the large-group capability, while attendees
    # are governed by the explicit required_trust_level stored on the event.
    # Treating target_size >= 6 as an attendee capability would contradict the
    # T1 "join 3+" rule and break the official cold-start inventory.
    if gathering.is_official:
        return None
    if gathering.target_size >= 6:
        return "large_group"
    if (gathering.official_metadata or {}).get("cross_college") is True:
        return "cross_college_matching"
    if gathering.mode == "complementary":
        return "competition_pool"
    if gathering.min_size <= 2:
        return "duo_gathering"
    return None


def join(
    db: Session,
    gathering_id: str,
    user: User,
    role: str | None,
    joined_via: str,
    *,
    backfill_intent_id: str | None = None,
) -> Gathering:
    with gathering_locks.acquire(gathering_id), user_locks.acquire(user.id):
        db.expire_all()
        gathering = get_gathering(db, gathering_id)
        if is_expired(gathering):
            _finalize_expired_locked(db, gathering)
            db.commit()
            raise AppError("GATHERING_EXPIRED", "本局招募已到期", 410)
        if gathering.status != GatheringStatus.POOLING.value:
            raise ConflictError("GATHERING_NOT_JOINABLE", "当前局不在招募状态")
        if not user.social_enabled:
            raise ForbiddenError("请先主动开启社交开关")
        if gathering.min_size < user.minimum_group_size and not _is_competition_team(
            db, gathering
        ):
            raise ConflictError(
                "GROUP_SIZE_BELOW_PREFERENCE",
                "本局最低成局人数低于你的个人设置",
                {"minimum_group_size": user.minimum_group_size},
            )
        members = active_members(db, gathering_id)
        existing = next((member for member in members if member.user_id == user.id), None)
        if existing:
            return gathering
        backfill_window = _backfill_window(gathering)
        backfill_intent: IntentCard | None = None
        if backfill_window is not None:
            if backfill_intent_id is None:
                raise ConflictError(
                    "BACKFILL_CLAIM_REQUIRED",
                    "补位缺口必须通过补位确认入口加入",
                )
            now = datetime.now(UTC)
            if now < backfill_window[1]:
                trust_service.require_unlock(db, user.id, "backfill_fast_lane")
            backfill_intent = _matching_backfill_intent(db, gathering, user.id)
            if backfill_intent is None or backfill_intent.id != backfill_intent_id:
                raise ForbiddenError("补位只对与本局类型相符的有效意图开放")
            joined_via = (
                "backfill_fast_lane" if now < backfill_window[1] else "backfill"
            )
        if len(members) >= gathering.target_size:
            raise ConflictError("GATHERING_FULL", "本局已满")
        if not (role or "").strip() and _is_competition_team(db, gathering):
            remaining = _remaining_required_roles(gathering, members)
            if len(remaining) == 1:
                role = remaining[0]
        capability = _join_trust_capability(gathering)
        if capability is not None:
            trust_service.require_unlock(db, user.id, capability)
        trust = trust_service.ensure_trust_profile(db, user.id)
        if LEVEL_ORDER[trust.level] < LEVEL_ORDER[gathering.required_trust_level]:
            details = {"required_level": gathering.required_trust_level}
            if capability is not None:
                details["capability"] = capability
            raise AppError(
                "TRUST_LEVEL_REQUIRED",
                f"本局要求 {gathering.required_trust_level} 及以上",
                403,
                details,
            )
        if _blocked_with_any(db, user.id, members):
            raise ForbiddenError("安全偏好不允许加入本局")
        member_users = [
            current for item in members if (current := db.get(User, item.user_id)) is not None
        ]
        if len(member_users) != len(members) or any(
            not current.social_enabled for current in member_users
        ):
            raise ConflictError(
                "GATHERING_PRIVACY_CHANGED",
                "成员的社交设置已变化，请刷新后重试",
            )
        if (
            gathering.same_gender_only
            or user.same_gender_only
            or any(current.same_gender_only for current in member_users)
        ):
            member_genders = {
                (current.gender_code or "").strip().lower() for current in member_users
            }
            user_gender = (user.gender_code or "").strip().lower()
            if (
                user_gender in {"", "unknown", "unspecified"}
                or bool(member_genders & {"", "unknown", "unspecified"})
                or any(gender != user_gender for gender in member_genders)
            ):
                raise ForbiddenError("本局启用了同性成员偏好")
        colleges = {
            college
            for current in [user, *member_users]
            if (college := (current.college or "").strip())
        }
        if len(colleges) > 1:
            trust_service.require_unlock(db, user.id, "cross_college_matching")
            if any(
                not trust_service.check_unlock(
                    db, current.id, "cross_college_matching"
                )
                for current in member_users
            ):
                raise ConflictError(
                    "CROSS_COLLEGE_TRUST_CHANGED",
                    "跨院系局要求全体成员达到 T2",
                )
        if _time_conflict(db, user.id, gathering):
            raise ConflictError("TIME_CONFLICT", "该时段已有其他局")
        prior = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.user_id == user.id,
            )
        )
        if prior:
            prior.left_at = None
            prior.role = role
            prior.joined_via = joined_via
            prior.confirmation_status = ConfirmationStatus.PENDING.value
            prior.confirmed_at = None
        else:
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user.id,
                    role=role,
                    joined_via=joined_via,
                )
            )
        if backfill_intent is not None:
            backfill_intent.status = IntentStatus.MATCHED.value
            # A backfill restores a group whose identities were already released
            # after its first confirmation round.  The replacement still waits
            # for every current member to reconfirm, but filling the original
            # minimum-size commitment is enough to restart that round.
            gathering.identity_disclosure = "after_confirmed"
        if user.identity_disclosure == "after_full" and backfill_window is None:
            if not _is_competition_team(db, gathering):
                gathering.identity_disclosure = "after_full"
        if user.same_gender_only:
            gathering.same_gender_only = True
        db.flush()
        roster = active_members(db, gathering.id)
        if _is_competition_team(db, gathering):
            if _competition_roster_ready(gathering, roster):
                transition(db, gathering, GatheringEvent.MATCHED, actor_user_id=user.id)
                _seal_competition_team(db, gathering, user.id)
        else:
            threshold = (
                gathering.min_size
                if backfill_window is not None
                else (
                    gathering.target_size
                    if gathering.is_official
                    or gathering.identity_disclosure == "after_full"
                    else gathering.min_size
                )
            )
            if len(roster) >= threshold:
                transition(db, gathering, GatheringEvent.MATCHED, actor_user_id=user.id)
                from onemore.modules.notify.service import notify_confirmation_required

                notify_confirmation_required(db, gathering)
        db.commit()
        return gathering


def confirm(db: Session, gathering_id: str, user_id: str, confirmed: bool) -> Gathering:
    with gathering_locks.acquire(gathering_id):
        gathering = get_gathering(db, gathering_id)
        member = require_member(db, gathering_id, user_id)
        if (
            confirmed
            and member.confirmation_status == ConfirmationStatus.CONFIRMED.value
            and gathering.status
            in {
                GatheringStatus.CONFIRMED.value,
                GatheringStatus.PREVIEWED.value,
                GatheringStatus.EXECUTED.value,
                GatheringStatus.ACTIVE.value,
                GatheringStatus.COMPLETED.value,
            }
        ):
            return gathering
        if gathering.status != GatheringStatus.TENTATIVE.value:
            raise ConflictError("GATHERING_NOT_CONFIRMABLE", "当前状态不接受确认")
        if not confirmed:
            return _leave_locked(
                db,
                gathering,
                member,
                user_id,
                silent_decline=True,
            )
        members = active_members(db, gathering_id)
        member_users = [db.get(User, item.user_id) for item in members]
        if len(member_users) != len(members) or any(
            current is None
            or not current.social_enabled
            or (
                gathering.min_size < current.minimum_group_size
                and not _is_competition_team(db, gathering)
            )
            for current in member_users
        ):
            raise ConflictError(
                "GATHERING_PRIVACY_CHANGED",
                "成员的社交设置已变化，请刷新后重试",
            )
        current_users = [current for current in member_users if current is not None]
        if any(
            LEVEL_ORDER[trust_service.ensure_trust_profile(db, current.id).level]
            < LEVEL_ORDER[gathering.required_trust_level]
            for current in current_users
        ):
            raise ConflictError(
                "GATHERING_TRUST_CHANGED",
                "成员当前等级不再满足本局门槛",
            )
        colleges = {
            college
            for current in current_users
            if (college := (current.college or "").strip())
        }
        if len(colleges) > 1 and any(
            not trust_service.check_unlock(
                db, current.id, "cross_college_matching"
            )
            for current in current_users
        ):
            raise ConflictError(
                "CROSS_COLLEGE_TRUST_CHANGED",
                "跨院系局要求全体成员达到 T2",
            )
        if gathering.same_gender_only or any(
            current.same_gender_only for current in current_users
        ):
            genders = {
                (current.gender_code or "").strip().lower()
                for current in current_users
            }
            if (
                len(genders) != 1
                or bool(genders.intersection({"", "unknown", "unspecified"}))
            ):
                raise ConflictError(
                    "GATHERING_PRIVACY_CHANGED",
                    "成员的同性偏好已变化，请刷新后重试",
                )
        if any(
            _blocked_with_any(
                db,
                current.id,
                [item for item in members if item.user_id != current.id],
            )
            for current in current_users
        ):
            raise ConflictError(
                "GATHERING_PRIVACY_CHANGED",
                "成员的安全设置已变化，请刷新后重试",
            )
        if member.confirmation_status == ConfirmationStatus.CONFIRMED.value:
            return gathering
        member.confirmation_status = ConfirmationStatus.CONFIRMED.value
        member.confirmed_at = utcnow()
        trust_service.record_event_once(db, user_id, "on_time_confirm", gathering_id)
        if len(members) >= gathering.min_size and all(
            item.confirmation_status == ConfirmationStatus.CONFIRMED.value for item in members
        ):
            transition(db, gathering, GatheringEvent.ALL_CONFIRMED, actor_user_id=user_id)
            from onemore.modules.collab.service import open_gathering_channel

            open_gathering_channel(db, gathering.id)
        db.commit()
        return gathering


def _leave_locked(
    db: Session,
    gathering: Gathering,
    member: GatheringMember,
    user_id: str,
    *,
    silent_decline: bool = False,
) -> Gathering:
    now = datetime.now(UTC)
    recorded_exit_event = False
    started = gathering.start_at is not None and now >= ensure_utc(gathering.start_at)
    if not silent_decline and started:
        # Once the activity has started, leaving must not let a confirmed
        # no-show choose the smaller pre-start late-exit penalty.
        trust_service.record_event_once(db, user_id, "no_show", gathering.id)
        recorded_exit_event = True
    elif not silent_decline and _is_late_exit(gathering, now):
        trust_service.record_event_once(db, user_id, "late_exit", gathering.id)
        recorded_exit_event = True
    if gathering.status == GatheringStatus.POOLING.value:
        db.delete(member)
        db.flush()
        remaining = db.scalar(
            select(GatheringMember.id).where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.left_at.is_(None),
            )
        )
        if remaining is None:
            transition(db, gathering, GatheringEvent.DISSOLVE, actor_user_id=user_id)
            if gathering.source_intent_id:
                intent = db.get(IntentCard, gathering.source_intent_id)
                if intent and intent.user_id == user_id:
                    intent.status = IntentStatus.WITHDRAWN.value
    else:
        previous_status = gathering.status
        if silent_decline:
            db.delete(member)
            candidate_intent = db.scalar(
                select(IntentCard)
                .where(
                    IntentCard.user_id == user_id,
                    IntentCard.gathering_type == gathering.gathering_type,
                    IntentCard.status == IntentStatus.MATCHED.value,
                )
                .order_by(IntentCard.updated_at.desc())
            )
            if candidate_intent:
                candidate_intent.status = IntentStatus.POOLING.value
        else:
            member.left_at = now
            member.confirmation_status = ConfirmationStatus.DECLINED.value
            leaving_intent = db.scalar(
                select(IntentCard)
                .where(
                    IntentCard.user_id == user_id,
                    IntentCard.gathering_type == gathering.gathering_type,
                    IntentCard.status == IntentStatus.MATCHED.value,
                )
                .order_by(IntentCard.updated_at.desc())
            )
            if leaving_intent:
                leaving_intent.status = IntentStatus.WITHDRAWN.value
        if gathering.status in {
            GatheringStatus.TENTATIVE.value,
            GatheringStatus.CONFIRMED.value,
            GatheringStatus.PREVIEWED.value,
            GatheringStatus.EXECUTED.value,
            GatheringStatus.ACTIVE.value,
        }:
            transition(
                db,
                gathering,
                GatheringEvent.MEMBER_LEFT,
                actor_user_id=None if silent_decline else user_id,
            )
            db.execute(
                update(GatheringMember)
                .where(
                    GatheringMember.gathering_id == gathering.id,
                    GatheringMember.left_at.is_(None),
                )
                .values(confirmation_status=ConfirmationStatus.PENDING.value, confirmed_at=None)
            )
            db.execute(
                update(CampusAction)
                .where(
                    CampusAction.gathering_id == gathering.id,
                    CampusAction.status == ActionStatus.PREVIEWED.value,
                )
                .values(status=ActionStatus.INVALIDATED.value)
            )
            channel = db.scalar(select(Channel).where(Channel.gathering_id == gathering.id))
            if channel:
                channel.status = ChannelStatus.CLOSED.value
            if previous_status in {
                GatheringStatus.EXECUTED.value,
                GatheringStatus.ACTIVE.value,
            }:
                from onemore.modules.notify.service import revoke_calendar

                revoke_calendar(db, gathering.id)
                # The original recruitment deadline is normally before the
                # start time.  Once an executed/active commitment loses a
                # member, the replacement window instead remains valid until
                # the event ends (or a bounded two-hour fallback).
                replacement_deadline = (
                    ensure_utc(gathering.end_at)
                    if gathering.end_at is not None
                    else now + timedelta(hours=2)
                )
                if replacement_deadline > now:
                    gathering.expires_at = replacement_deadline
            db.flush()
            remaining = db.scalar(
                select(GatheringMember.id).where(
                    GatheringMember.gathering_id == gathering.id,
                    GatheringMember.left_at.is_(None),
                )
            )
            if remaining is None and gathering.status in {
                GatheringStatus.POOLING.value,
                GatheringStatus.TENTATIVE.value,
            }:
                transition(db, gathering, GatheringEvent.DISSOLVE)
                db.execute(
                    delete(GatheringMember).where(GatheringMember.gathering_id == gathering.id)
                )
        if gathering.status == GatheringStatus.POOLING.value:
            _notify_backfill_candidates(db, gathering, departed_user_id=user_id)
    if recorded_exit_event:
        trust_service.recompute_level(db, user_id)
    else:
        db.commit()
    return gathering


def _is_late_exit(gathering: Gathering, now: datetime) -> bool:
    start_at = ensure_utc(gathering.start_at) if gathering.start_at is not None else None
    return bool(
        gathering.status
        in {
            GatheringStatus.CONFIRMED.value,
            GatheringStatus.PREVIEWED.value,
            GatheringStatus.EXECUTED.value,
            GatheringStatus.ACTIVE.value,
        }
        and start_at is not None
        and start_at - timedelta(hours=2) <= now < start_at
    )


def _leave_capability(gathering: Gathering) -> dict:
    now = datetime.now(UTC)
    started = gathering.start_at is not None and now >= ensure_utc(gathering.start_at)
    terminal = gathering.status in TERMINAL_GATHERING_STATES
    unavailable = terminal
    late = not unavailable and not started and _is_late_exit(gathering, now)
    cutoff = (
        ensure_utc(gathering.start_at) - timedelta(hours=2)
        if gathering.start_at is not None
        else None
    )
    if terminal:
        message = "本局已结束，不再接受退出操作。"
    elif started:
        message = "本局已开始；确认退出会按未履约记录，不能改记为较轻的临期退出。"
    elif late:
        message = "当前已进入开始前 2 小时内；确认退出会记录一次临期退出并影响信任进度。"
    else:
        message = "现在退出属于提前取消，不影响信任等级；退出原因不会向其他成员展示。"
    return {
        "enabled": not unavailable,
        "trust_impact": "no_show" if started and not terminal else "late_exit" if late else "none",
        "message": message,
        "late_exit_cutoff": cutoff,
        "server_now": now,
        "disabled_reason": "本局已结束" if terminal else None,
    }


def _notify_backfill_candidates(
    db: Session, gathering: Gathering, *, departed_user_id: str
) -> None:
    members = active_members(db, gathering.id)
    if not members:
        return
    active_ids = {member.user_id for member in members}
    query = select(IntentCard).where(
        IntentCard.status == IntentStatus.POOLING.value,
        IntentCard.gathering_type == gathering.gathering_type,
        IntentCard.user_id.not_in(active_ids),
        IntentCard.expires_at > datetime.now(UTC),
    )
    if gathering.campus:
        query = query.where(
            or_(IntentCard.campus.is_(None), IntentCard.campus == gathering.campus)
        )
    candidates = list(db.scalars(query.order_by(IntentCard.updated_at.desc()).limit(30)))
    opened_at = datetime.now(UTC)
    fast_lane_until = opened_at + timedelta(minutes=15)
    if gathering.expires_at is not None:
        fast_lane_until = min(fast_lane_until, ensure_utc(gathering.expires_at))
    metadata = dict(gathering.official_metadata or {})
    metadata["backfill"] = {
        "opened_at": opened_at.isoformat(),
        "fast_lane_until": fast_lane_until.isoformat(),
        "departed_user_id": departed_user_id,
    }
    gathering.official_metadata = metadata
    from onemore.modules.notify.service import push

    ranked = sorted(
        candidates,
        key=lambda card: (
            not trust_service.check_unlock(db, card.user_id, "backfill_fast_lane"),
            -ensure_utc(card.updated_at).timestamp(),
        ),
    )
    for card in ranked:
        if any(
            users_have_block_between(db, card.user_id, member_id)
            for member_id in active_ids
        ):
            continue
        fast_lane = trust_service.check_unlock(
            db, card.user_id, "backfill_fast_lane"
        )
        push(
            db,
            card.user_id,
            "backfill_invitation",
            {
                "gathering_id": gathering.id,
                "deep_link": f"onemore://gathering/{gathering.id}",
                "summary": "有一个与你当前意图相符的补位机会",
                "fast_lane": fast_lane,
                "claim_available_at": (
                    opened_at if fast_lane else fast_lane_until
                ).isoformat(),
                "history_visible": False,
            },
            dedupe_key=f"backfill:{gathering.id}:{departed_user_id}:{card.user_id}",
        )


def _matching_backfill_intent(
    db: Session, gathering: Gathering, user_id: str
) -> IntentCard | None:
    query = (
        select(IntentCard)
        .where(
            IntentCard.user_id == user_id,
            IntentCard.status == IntentStatus.POOLING.value,
            IntentCard.gathering_type == gathering.gathering_type,
            IntentCard.expires_at > datetime.now(UTC),
        )
        .order_by(IntentCard.updated_at.desc())
    )
    if gathering.campus:
        query = query.where(
            or_(IntentCard.campus.is_(None), IntentCard.campus == gathering.campus)
        )
    return db.scalar(query)


def _backfill_window(gathering: Gathering) -> tuple[datetime, datetime] | None:
    raw = (gathering.official_metadata or {}).get("backfill")
    if not isinstance(raw, dict):
        return None
    opened_raw = raw.get("opened_at")
    until_raw = raw.get("fast_lane_until")
    if not isinstance(opened_raw, str) or not isinstance(until_raw, str):
        return None
    try:
        return ensure_utc(datetime.fromisoformat(opened_raw)), ensure_utc(
            datetime.fromisoformat(until_raw)
        )
    except ValueError:
        return None


def _backfill_fallback_options(db: Session, gathering: Gathering) -> list[dict]:
    members = active_members(db, gathering.id)
    users = [db.get(User, item.user_id) for item in members]
    options: list[dict] = []
    kind = f"{gathering.gathering_type} {gathering.title}"
    if (
        len(members) >= 2
        and any(value in kind for value in ("羽毛球", "网球", "乒乓", "双打", "运动"))
        and all(user is not None and user.minimum_group_size <= 2 for user in users)
        and all(
            user is not None
            and trust_service.check_unlock(db, user.id, "duo_gathering")
            for user in users
        )
    ):
        options.append(
            {
                "key": "sport_practice_duo",
                "title": "双打改为两人练球",
                "summary": "保留当前时段与场地，改为两人练习；仍需双方重新确认。",
                "min_size": 2,
                "target_size": 2,
                "location": gathering.location,
            }
        )
    if gathering.target_size >= 4:
        options.append(
            {
                "key": "reduce_to_three",
                "title": "4 人方案改为 3 人",
                "summary": "缩小分工范围，三人即可成局；所有当前成员重新确认。",
                "min_size": 3,
                "target_size": 3,
                "location": gathering.location,
            }
        )
    if gathering.location != "线上":
        options.append(
            {
                "key": "move_online",
                "title": "线下改为线上",
                "summary": "保留目标与人数，改为线上协作并重新开放一天补位。",
                "min_size": gathering.min_size,
                "target_size": gathering.target_size,
                "location": "线上",
            }
        )
    return options


def backfill_opportunity(db: Session, gathering_id: str, user_id: str) -> dict:
    gathering = get_gathering(db, gathering_id)
    window = _backfill_window(gathering)
    member = db.scalar(
        select(GatheringMember.id).where(
            GatheringMember.gathering_id == gathering.id,
            GatheringMember.user_id == user_id,
            GatheringMember.left_at.is_(None),
        )
    )
    intent = _matching_backfill_intent(db, gathering, user_id)
    if member is None and intent is None:
        raise ForbiddenError("补位面板仅对当前成员或匹配到的意图持有人开放")
    now = datetime.now(UTC)
    fast_lane = trust_service.check_unlock(db, user_id, "backfill_fast_lane")
    until = window[1] if window else None
    is_open = bool(
        window
        and gathering.status == GatheringStatus.POOLING.value
        and not is_expired(gathering, now)
    )
    return {
        "gathering_id": gathering.id,
        "open": is_open,
        "fast_lane_active": bool(is_open and until and now < until),
        "fast_lane_until": until,
        "viewer_fast_lane_eligible": fast_lane,
        "viewer_has_matching_intent": intent is not None,
        "claim_available_at": (
            now if fast_lane else until
        )
        if is_open
        else None,
        # A replacement starts with the current state and never receives past
        # channel messages or collaboration history.
        "history_visible": False,
        "viewer_is_member": member is not None,
        # Fallbacks belong to a real replacement incident.  A normal Pooling
        # gathering must never render executable-looking recovery actions
        # whose POST endpoint will reject with BACKFILL_NOT_OPEN.
        "fallback_options": (
            _backfill_fallback_options(db, gathering)
            if member is not None and window is not None and not is_expired(gathering, now)
            else []
        ),
    }


def claim_backfill(
    db: Session,
    gathering_id: str,
    user: User,
    role: str | None,
) -> Gathering:
    gathering = get_gathering(db, gathering_id)
    window = _backfill_window(gathering)
    if window is None or gathering.status != GatheringStatus.POOLING.value:
        raise ConflictError("BACKFILL_NOT_OPEN", "当前没有开放的补位缺口")
    now = datetime.now(UTC)
    if now < window[1]:
        trust_service.require_unlock(db, user.id, "backfill_fast_lane")
    intent = _matching_backfill_intent(db, gathering, user.id)
    if intent is None:
        raise ForbiddenError("需要先有与本局类型相符的有效意图卡")
    selected_role = role or (
        intent.capabilities[0].get("key") if intent.capabilities else None
    )
    item = join(
        db,
        gathering_id,
        user,
        selected_role,
        "backfill",
        backfill_intent_id=intent.id,
    )
    return item


def apply_backfill_fallback(
    db: Session,
    gathering_id: str,
    user_id: str,
    option_key: str,
) -> Gathering:
    with gathering_locks.acquire(gathering_id):
        db.expire_all()
        gathering = get_gathering(db, gathering_id)
        require_member(db, gathering_id, user_id)
        now = datetime.now(UTC)
        if (
            _backfill_window(gathering) is None
            or gathering.status != GatheringStatus.POOLING.value
            or is_expired(gathering, now)
        ):
            raise ConflictError("BACKFILL_NOT_OPEN", "当前没有可降级的补位缺口")
        option = next(
            (
                item
                for item in _backfill_fallback_options(db, gathering)
                if item["key"] == option_key
            ),
            None,
        )
        if option is None:
            raise AppError("UNKNOWN_BACKFILL_FALLBACK", "该降级方案不适用于当前局", 422)
        members = active_members(db, gathering.id)
        member_users = [db.get(User, item.user_id) for item in members]
        if any(
            current is None
            or current.account_status != "active"
            or not current.social_enabled
            or int(option["min_size"]) < current.minimum_group_size
            for current in member_users
        ):
            raise ConflictError(
                "BACKFILL_FALLBACK_PRIVACY_CONFLICT",
                "降级人数与当前成员设置冲突",
            )
        current_users = [current for current in member_users if current is not None]
        if any(
            users_have_block_between(db, left.id, right.id)
            for index, left in enumerate(current_users)
            for right in current_users[index + 1 :]
        ):
            raise ConflictError(
                "BACKFILL_FALLBACK_MEMBER_BLOCKED",
                "成员间的安全设置已变化，不能采用该方案",
            )
        if gathering.same_gender_only or any(
            current.same_gender_only for current in current_users
        ):
            genders = {
                (current.gender_code or "").strip().lower()
                for current in current_users
            }
            if len(genders) != 1 or bool(
                genders.intersection({"", "unknown", "unspecified"})
            ):
                raise ConflictError(
                    "BACKFILL_FALLBACK_PRIVACY_CONFLICT",
                    "成员的同性偏好已变化，不能采用该方案",
                )
        if any(
            LEVEL_ORDER[trust_service.ensure_trust_profile(db, current.id).level]
            < LEVEL_ORDER[gathering.required_trust_level]
            for current in current_users
        ):
            raise ConflictError(
                "BACKFILL_FALLBACK_TRUST_CONFLICT",
                "成员当前信任等级不再满足本局门槛",
            )
        colleges = {
            college
            for current in current_users
            if (college := (current.college or "").strip())
        }
        if len(colleges) > 1 and any(
            not trust_service.check_unlock(
                db, current.id, "cross_college_matching"
            )
            for current in current_users
        ):
            raise ConflictError(
                "BACKFILL_FALLBACK_TRUST_CONFLICT",
                "跨院系局要求全体成员达到 T2",
            )
        if int(option["min_size"]) <= 2 and any(
            current is None
            or not trust_service.check_unlock(db, current.id, "duo_gathering")
            for current in member_users
        ):
            raise ConflictError(
                "BACKFILL_FALLBACK_TRUST_CONFLICT",
                "两人降级方案要求当前成员都达到 T2",
            )
        gathering.min_size = int(option["min_size"])
        gathering.target_size = int(option["target_size"])
        gathering.location = option["location"]
        gathering.goal = f"{gathering.goal}（已采用：{option['title']}）"
        metadata = dict(gathering.official_metadata or {})
        metadata.pop("backfill", None)
        metadata["backfill_fallback"] = {
            "key": option["key"],
            "title": option["title"],
            "applied_by": user_id,
            "applied_at": datetime.now(UTC).isoformat(),
        }
        gathering.official_metadata = metadata
        # Never reopen recruitment beyond the real activity boundary.  For a
        # future activity recruitment closes at its start; for an in-progress
        # repair it closes at the end.
        recruitment_deadline = now + timedelta(days=1)
        if gathering.start_at is not None and ensure_utc(gathering.start_at) > now:
            recruitment_deadline = min(
                recruitment_deadline, ensure_utc(gathering.start_at)
            )
        if gathering.end_at is not None:
            recruitment_deadline = min(
                recruitment_deadline, ensure_utc(gathering.end_at)
            )
        if recruitment_deadline <= now:
            raise ConflictError("GATHERING_ENDED", "本局已经结束，不能重新招募")
        gathering.expires_at = recruitment_deadline
        if len(members) >= gathering.min_size:
            transition(db, gathering, GatheringEvent.MATCHED, actor_user_id=user_id)
            from onemore.modules.notify.service import notify_confirmation_required

            notify_confirmation_required(db, gathering)
        db.commit()
        db.refresh(gathering)
        return gathering


def leave(db: Session, gathering_id: str, user_id: str, reason: str | None = None) -> Gathering:
    with gathering_locks.acquire(gathering_id):
        gathering = get_gathering(db, gathering_id)
        member = require_member(db, gathering_id, user_id)
        if gathering.status in TERMINAL_GATHERING_STATES:
            raise ConflictError(
                "GATHERING_LEAVE_CLOSED",
                "本局已结束，不再接受退出操作",
                {"status": gathering.status},
            )
        # `reason` is user-authored private context, never an internal control
        # flag.  Only confirm(false) can select the silent-decline branch.
        return _leave_locked(
            db,
            gathering,
            member,
            user_id,
            silent_decline=False,
        )


def time_options(db: Session, gathering_id: str, user_id: str) -> list:
    require_member(db, gathering_id, user_id)
    members = active_members(db, gathering_id)
    return schedule_service.intersect_windows(
        db, [member.user_id for member in members], minimum_minutes=60
    )


def propose_reschedule(
    db: Session, gathering_id: str, user_id: str, start_at: datetime, end_at: datetime
) -> RescheduleProposal:
    with gathering_locks.acquire(gathering_id):
        gathering = get_gathering(db, gathering_id)
        require_member(db, gathering_id, user_id)
        if gathering.status not in {
            GatheringStatus.TENTATIVE.value,
            GatheringStatus.CONFIRMED.value,
            GatheringStatus.PREVIEWED.value,
        }:
            raise ConflictError("RESCHEDULE_NOT_AVAILABLE", "当前状态不接受改约提议")
        now = datetime.now(UTC)
        if ensure_utc(start_at) <= now + timedelta(minutes=5):
            raise ConflictError("RESCHEDULE_TIME_TOO_SOON", "改约时间必须至少晚于当前 5 分钟")
        existing = db.scalar(
            select(RescheduleProposal)
            .where(
                RescheduleProposal.gathering_id == gathering_id,
                RescheduleProposal.status == "open",
            )
            .order_by(RescheduleProposal.created_at.desc())
        )
        if existing is not None:
            if existing.expires_at is not None and ensure_utc(existing.expires_at) <= now:
                existing.status = "expired"
                existing.decided_at = now
                db.flush()
            elif (
                existing.proposed_by == user_id
                and ensure_utc(existing.start_at) == ensure_utc(start_at)
                and ensure_utc(existing.end_at) == ensure_utc(end_at)
            ):
                return existing
            else:
                raise ConflictError(
                    "RESCHEDULE_VOTE_IN_PROGRESS",
                    "已有一项匿名改约提议等待成员确认",
                    {"proposal_id": existing.id},
                )
        options = time_options(db, gathering_id, user_id)
        selected = next(
            (
                option
                for option in options
                if ensure_utc(option.start_at) <= ensure_utc(start_at)
                and ensure_utc(option.end_at) >= ensure_utc(end_at)
            ),
            None,
        )
        if selected is None:
            raise ConflictError("TIME_NOT_FEASIBLE", "该时段不是全员共同可行时间")
        members = active_members(db, gathering_id)
        eligible_user_ids = sorted(member.user_id for member in members)
        if selected.feasible_count < len(eligible_user_ids):
            raise ConflictError("TIME_NOT_FEASIBLE", "该时段不是全员共同可行时间")
        decision_deadline = now + timedelta(minutes=30)
        if gathering.start_at is not None:
            decision_deadline = min(decision_deadline, ensure_utc(gathering.start_at))
        if decision_deadline <= now:
            raise ConflictError("RESCHEDULE_VOTE_TOO_LATE", "原定开始时间已到，不能发起改约")
        proposal = RescheduleProposal(
            gathering_id=gathering_id,
            proposed_by=user_id,
            start_at=start_at,
            end_at=end_at,
            feasible_count=selected.feasible_count,
            status="open",
            eligible_user_ids=eligible_user_ids,
            expires_at=decision_deadline,
        )
        db.add(proposal)
        db.flush()
        db.add(
            RescheduleVote(
                proposal_id=proposal.id,
                user_id=user_id,
                accepted=True,
            )
        )
        db.flush()
        from onemore.modules.notify.service import push

        for member in members:
            if member.user_id == user_id:
                continue
            push(
                db,
                member.user_id,
                "reschedule_vote_required",
                {
                    "gathering_id": gathering_id,
                    "deep_link": f"onemore://gathering/{gathering_id}/space",
                    "summary": "有一项共同可行的改约时间等待匿名确认",
                },
                dedupe_key=f"reschedule-vote:{proposal.id}",
            )
        if len(eligible_user_ids) == 1:
            _accept_reschedule_proposal(db, gathering, proposal)
        db.commit()
        db.refresh(proposal)
        return proposal


def _expire_reschedule_proposal(
    db: Session, proposal: RescheduleProposal, *, commit: bool = False
) -> bool:
    if (
        proposal.status == "open"
        and proposal.expires_at is not None
        and ensure_utc(proposal.expires_at) <= datetime.now(UTC)
    ):
        proposal.status = "expired"
        proposal.decided_at = utcnow()
        if commit:
            db.commit()
            db.refresh(proposal)
        return True
    return False


def reschedule_proposal_view(
    db: Session, proposal: RescheduleProposal, user_id: str
) -> dict:
    require_member(db, proposal.gathering_id, user_id)
    _expire_reschedule_proposal(db, proposal, commit=True)
    votes = list(
        db.scalars(
            select(RescheduleVote).where(RescheduleVote.proposal_id == proposal.id)
        )
    )
    mine = next((vote for vote in votes if vote.user_id == user_id), None)
    return {
        "proposal_id": proposal.id,
        "gathering_id": proposal.gathering_id,
        "status": proposal.status,
        "start_at": proposal.start_at,
        "end_at": proposal.end_at,
        "feasible_count": proposal.feasible_count,
        "accepted_count": sum(vote.accepted for vote in votes),
        "required_count": len(proposal.eligible_user_ids or []),
        "my_vote": (
            "accepted" if mine and mine.accepted else "declined" if mine else None
        ),
        "expires_at": proposal.expires_at,
        "decided_at": proposal.decided_at,
    }


def current_reschedule_proposal(
    db: Session, gathering_id: str, user_id: str
) -> RescheduleProposal | None:
    require_member(db, gathering_id, user_id)
    proposal = db.scalar(
        select(RescheduleProposal)
        .where(RescheduleProposal.gathering_id == gathering_id)
        .order_by(RescheduleProposal.created_at.desc())
    )
    if proposal is not None:
        _expire_reschedule_proposal(db, proposal, commit=True)
    return proposal


def _accept_reschedule_proposal(
    db: Session,
    gathering: Gathering,
    proposal: RescheduleProposal,
) -> None:
    current_ids = sorted(member.user_id for member in active_members(db, gathering.id))
    if current_ids != sorted(proposal.eligible_user_ids or []):
        proposal.status = "invalidated"
        proposal.decided_at = utcnow()
        return
    if gathering.status not in {
        GatheringStatus.TENTATIVE.value,
        GatheringStatus.CONFIRMED.value,
        GatheringStatus.PREVIEWED.value,
    }:
        proposal.status = "invalidated"
        proposal.decided_at = utcnow()
        return
    options = schedule_service.intersect_windows(
        db, current_ids, minimum_minutes=60
    )
    still_feasible = any(
        ensure_utc(option.start_at) <= ensure_utc(proposal.start_at)
        and ensure_utc(option.end_at) >= ensure_utc(proposal.end_at)
        and option.feasible_count >= len(current_ids)
        for option in options
    )
    if not still_feasible:
        proposal.status = "invalidated"
        proposal.decided_at = utcnow()
        return
    gathering.start_at = proposal.start_at
    gathering.end_at = proposal.end_at
    db.execute(
        update(CampusAction)
        .where(
            CampusAction.gathering_id == gathering.id,
            CampusAction.status == ActionStatus.PREVIEWED.value,
        )
        .values(status=ActionStatus.INVALIDATED.value)
    )
    transition(db, gathering, GatheringEvent.RESCHEDULE, actor_user_id=None)
    gathering.confirmation_deadline = utcnow() + timedelta(minutes=15)
    db.execute(
        update(GatheringMember)
        .where(
            GatheringMember.gathering_id == gathering.id,
            GatheringMember.left_at.is_(None),
        )
        .values(
            confirmation_status=ConfirmationStatus.PENDING.value,
            confirmed_at=None,
        )
    )
    proposal.status = "accepted"
    proposal.decided_at = utcnow()
    db.flush()
    from onemore.modules.notify.service import push

    for member in active_members(db, gathering.id):
        push(
            db,
            member.user_id,
            "gathering_rescheduled",
            {
                "gathering_id": gathering.id,
                "deep_link": f"onemore://gathering/{gathering.id}/space",
                "calendar_event": {
                    "title": gathering.title,
                    "start_at": ensure_utc(proposal.start_at)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "end_at": ensure_utc(proposal.end_at)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "location": gathering.location,
                },
            },
            dedupe_key=f"reschedule:{proposal.id}",
        )


def vote_reschedule(
    db: Session,
    gathering_id: str,
    proposal_id: str,
    user_id: str,
    accepted: bool,
) -> RescheduleProposal:
    with gathering_locks.acquire(gathering_id):
        gathering = get_gathering(db, gathering_id)
        require_member(db, gathering_id, user_id)
        proposal = db.get(RescheduleProposal, proposal_id)
        if proposal is None or proposal.gathering_id != gathering_id:
            raise NotFoundError("改约提议", proposal_id)
        if user_id not in set(proposal.eligible_user_ids or []):
            raise ForbiddenError("你不在这项改约提议的匿名确认范围内")
        if _expire_reschedule_proposal(db, proposal):
            db.commit()
            raise ConflictError("RESCHEDULE_VOTE_EXPIRED", "改约提议已过期")
        existing = db.scalar(
            select(RescheduleVote).where(
                RescheduleVote.proposal_id == proposal.id,
                RescheduleVote.user_id == user_id,
            )
        )
        if proposal.status != "open":
            if existing is not None and existing.accepted == accepted:
                return proposal
            raise ConflictError(
                "RESCHEDULE_VOTE_CLOSED",
                "改约提议已经结束",
                {"status": proposal.status},
            )
        if existing is None:
            existing = RescheduleVote(
                proposal_id=proposal.id,
                user_id=user_id,
                accepted=accepted,
            )
            db.add(existing)
        else:
            existing.accepted = accepted
            existing.decided_at = utcnow()
        db.flush()
        if not accepted:
            proposal.status = "rejected"
            proposal.decided_at = utcnow()
            from onemore.modules.notify.service import push

            for member_id in proposal.eligible_user_ids or []:
                push(
                    db,
                    member_id,
                    "reschedule_vote_rejected",
                    {
                        "gathering_id": gathering_id,
                        "deep_link": f"onemore://gathering/{gathering_id}/space",
                        "summary": "本次匿名改约提议未通过，原时间保持不变",
                    },
                    dedupe_key=f"reschedule-rejected:{proposal.id}",
                )
        else:
            votes = list(
                db.scalars(
                    select(RescheduleVote).where(
                        RescheduleVote.proposal_id == proposal.id,
                        RescheduleVote.accepted.is_(True),
                    )
                )
            )
            if len(votes) == len(proposal.eligible_user_ids or []):
                _accept_reschedule_proposal(db, gathering, proposal)
        db.commit()
        db.refresh(proposal)
        return proposal


def _completion_outcome(
    db: Session, gathering_id: str, user_id: str
) -> str | None:
    event = db.scalar(
        select(TrustEvent.event_type)
        .where(
            TrustEvent.user_id == user_id,
            TrustEvent.reference_id == gathering_id,
            TrustEvent.event_type.in_(
                ["completion_confirmed", "no_show", "completion_unresolved"]
            ),
        )
        .order_by(TrustEvent.occurred_at.desc())
    )
    return event


def _finalize_completion_if_resolved(
    db: Session, gathering: Gathering, actor_user_id: str | None = None
) -> bool:
    members = active_members(db, gathering.id)
    if not members or not all(
        item.completion_confirmed
        or _completion_outcome(db, gathering.id, item.user_id)
        in {"no_show", "completion_unresolved"}
        for item in members
    ):
        return False
    transition(db, gathering, GatheringEvent.COMPLETE, actor_user_id=actor_user_id)
    gathering.completed_at = utcnow()
    from onemore.modules.collab.service import record_experience

    record_experience(db, gathering.id)
    _record_recurrence_trust_after_completion(db, gathering, members)
    for item in members:
        trust_service.recompute_level(db, item.user_id)
    return True


def _record_recurrence_trust_after_completion(
    db: Session,
    gathering: Gathering,
    members: list[GatheringMember],
) -> None:
    """Record recurrence only for a fulfilled reunion with an original peer."""

    metadata = gathering.official_metadata or {}
    created_via = metadata.get("created_via")
    if created_via not in {"recurrence_choice", "recurring_gathering"}:
        return
    completed_ids = {item.user_id for item in members if item.completion_confirmed}
    if created_via == "recurrence_choice":
        parent_id = metadata.get("parent_gathering_id")
        if not isinstance(parent_id, str):
            return
        original_ids = set(
            db.scalars(
                select(GatheringMember.user_id).where(
                    GatheringMember.gathering_id == parent_id,
                    GatheringMember.left_at.is_(None),
                )
            )
        )
        completed_ids &= original_ids
    if len(completed_ids) < 2:
        return
    for member_id in completed_ids:
        trust_service.record_event_once(db, member_id, "recurred", gathering.id)


def complete(db: Session, gathering_id: str, user_id: str, completed: bool) -> Gathering:
    with gathering_locks.acquire(gathering_id):
        gathering = get_gathering(db, gathering_id)
        member = require_member(db, gathering_id, user_id)
        if (
            completed
            and member.completion_confirmed
            and gathering.status
            in {
                GatheringStatus.COMPLETED.value,
                GatheringStatus.RECURRENCE_PENDING.value,
                GatheringStatus.ARCHIVED.value,
            }
        ):
            return gathering
        if gathering.status not in {GatheringStatus.EXECUTED.value, GatheringStatus.ACTIVE.value}:
            raise ConflictError("GATHERING_NOT_COMPLETABLE", "当前局尚不可完成")
        now = datetime.now(UTC)
        if gathering.end_at is None or ensure_utc(gathering.end_at) > now:
            raise ConflictError(
                "GATHERING_NOT_ENDED",
                "本局结束后才可提交完成确认",
                {
                    "end_at": (
                        ensure_utc(gathering.end_at).isoformat()
                        if gathering.end_at is not None
                        else None
                    )
                },
            )
        prior_outcome = _completion_outcome(db, gathering_id, user_id)
        if completed and member.completion_confirmed:
            return gathering
        if not completed and prior_outcome == "no_show":
            return gathering
        if member.completion_confirmed and not completed:
            raise ConflictError("COMPLETION_ALREADY_CONFIRMED", "完成确认不可撤回")
        if completed:
            if prior_outcome in {"no_show", "completion_unresolved"}:
                raise ConflictError("COMPLETION_ALREADY_RECORDED", "完成结果已经记录")
            member.completion_confirmed = True
            trust_service.record_event_once(
                db, user_id, "completion_confirmed", gathering_id
            )
            from onemore.modules.collab.service import record_goal_member_progress

            record_goal_member_progress(db, gathering_id, user_id)
        else:
            trust_service.record_event_once(db, user_id, "no_show", gathering_id)
        _finalize_completion_if_resolved(db, gathering, actor_user_id=user_id)
        db.commit()
        return gathering


def recur(
    db: Session, gathering_id: str, user_id: str, keep_user_ids: list[str] | None
) -> Gathering:
    with gathering_locks.acquire(gathering_id):
        original = get_gathering(db, gathering_id)
        require_member(db, gathering_id, user_id)
        existing = db.scalar(
            select(GatheringRecurrenceDecision).where(
                GatheringRecurrenceDecision.gathering_id == gathering_id,
                GatheringRecurrenceDecision.user_id == user_id,
            )
        )
        if existing is not None:
            if existing.clone_gathering_id:
                clone = db.get(Gathering, existing.clone_gathering_id)
                if clone is not None:
                    return clone
            raise ConflictError("RECURRENCE_ALREADY_ENDED", "你已安静结束本次复局选择")
        if original.status != GatheringStatus.COMPLETED.value:
            raise ConflictError("GATHERING_NOT_RECURRABLE", "只有已完成的局可复局")
        current_ids = [member.user_id for member in active_members(db, gathering_id)]
        requested = current_ids if keep_user_ids is None else list(dict.fromkeys(keep_user_ids))
        if any(item not in current_ids for item in requested):
            raise AppError("INVALID_RECUR_MEMBERS", "只能保留原局当前成员", 422)
        kept = [item for item in requested if item in current_ids]
        if user_id not in kept:
            kept.append(user_id)
        users = [db.get(User, member_id) for member_id in kept]
        if len(users) != len(kept) or any(
            member is None
            or member.account_status != "active"
            or not member.social_enabled
            or original.min_size < member.minimum_group_size
            for member in users
        ):
            raise ConflictError(
                "RECUR_MEMBER_PRIVACY_CHANGED",
                "保留成员的社交或最低人数设置已变化",
            )
        current_users = [member for member in users if member is not None]
        if any(
            users_have_block_between(db, left.id, right.id)
            for index, left in enumerate(current_users)
            for right in current_users[index + 1 :]
        ):
            raise ConflictError("RECUR_MEMBER_BLOCKED", "成员间安全设置已变化")
        if original.same_gender_only or any(
            member.same_gender_only for member in current_users
        ):
            genders = {
                (member.gender_code or "").strip().lower()
                for member in current_users
            }
            if len(genders) != 1 or bool(
                genders.intersection({"", "unknown", "unspecified"})
            ):
                raise ConflictError(
                    "RECUR_MEMBER_PRIVACY_CHANGED",
                    "成员的同性偏好已变化",
                )
        if any(
            LEVEL_ORDER[trust_service.ensure_trust_profile(db, member.id).level]
            < LEVEL_ORDER[original.required_trust_level]
            for member in current_users
        ):
            raise ConflictError("RECUR_MEMBER_TRUST_CHANGED", "成员当前信任等级不足")
        colleges = {
            college
            for member in current_users
            if (college := (member.college or "").strip())
        }
        if len(colleges) > 1 and any(
            not trust_service.check_unlock(db, member.id, "cross_college_matching")
            for member in current_users
        ):
            raise ConflictError(
                "RECUR_MEMBER_TRUST_CHANGED",
                "跨院系复局要求全体成员达到 T2",
            )

        now = datetime.now(UTC)
        duration = (
            ensure_utc(original.end_at) - ensure_utc(original.start_at)
            if original.start_at is not None and original.end_at is not None
            else timedelta(hours=2)
        )
        start_at = (
            ensure_utc(original.start_at) + timedelta(days=7)
            if original.start_at is not None
            else now + timedelta(days=1)
        )
        while start_at <= now + timedelta(minutes=30):
            start_at += timedelta(days=7)
        end_at = start_at + duration
        expires_at = max(now + timedelta(minutes=5), start_at - timedelta(minutes=30))
        recurrence_intent = IntentCard(
            user_id=user_id,
            status=IntentStatus.POOLING.value,
            gathering_type=original.gathering_type,
            mode=original.mode,
            goal=original.goal,
            capabilities=[],
            required_roles=original.required_roles,
            intensity="balanced",
            available_windows=[
                {
                    "start_at": start_at.isoformat(),
                    "end_at": end_at.isoformat(),
                    "stability": 1.0,
                }
            ],
            campus=original.campus,
            min_size=original.min_size,
            target_size=original.target_size,
            social_mode=original.identity_disclosure,
            same_gender_only=original.same_gender_only,
            expires_at=expires_at,
            field_sources={"all": "shared_experience_recurrence"},
        )
        db.add(recurrence_intent)
        db.flush()
        clone = Gathering(
            source_intent_id=recurrence_intent.id,
            owner_user_id=user_id,
            gathering_type=original.gathering_type,
            mode=original.mode,
            title=original.title,
            goal=original.goal,
            status=GatheringStatus.POOLING.value,
            min_size=original.min_size,
            target_size=original.target_size,
            required_trust_level=original.required_trust_level,
            campus=original.campus,
            same_gender_only=original.same_gender_only,
            identity_disclosure=original.identity_disclosure,
            start_at=start_at,
            end_at=end_at,
            location=original.location,
            required_roles=original.required_roles,
            official_metadata={
                "created_via": "recurrence_choice",
                "parent_gathering_id": original.id,
                "choice": "same_group" if keep_user_ids is None else "partial",
            },
            expires_at=expires_at,
        )
        db.add(clone)
        db.flush()
        if any(_time_conflict(db, member_id, clone) for member_id in kept):
            raise ConflictError("RECUR_TIME_CONFLICT", "至少一位保留成员在下周时段已有其他局")
        for member_id in kept:
            db.add(
                GatheringMember(
                    gathering_id=clone.id,
                    user_id=member_id,
                    joined_via="recur",
                )
            )
        db.flush()
        threshold = (
            clone.target_size
            if clone.identity_disclosure == "after_full"
            else clone.min_size
        )
        if len(kept) >= threshold:
            transition(db, clone, GatheringEvent.MATCHED, actor_user_id=user_id)
            recurrence_intent.status = IntentStatus.MATCHED.value
            from onemore.modules.notify.service import notify_confirmation_required

            notify_confirmation_required(db, clone)
        db.add(
            GatheringRecurrenceDecision(
                gathering_id=original.id,
                user_id=user_id,
                decision="same_group" if keep_user_ids is None else "partial",
                kept_user_ids=kept,
                clone_gathering_id=clone.id,
            )
        )
        db.commit()
        db.refresh(clone)
        return clone


def finish_recurrence_choice(db: Session, gathering_id: str, user_id: str) -> dict:
    with gathering_locks.acquire(gathering_id):
        gathering = get_gathering(db, gathering_id)
        require_member(db, gathering_id, user_id)
        if gathering.status != GatheringStatus.COMPLETED.value:
            raise ConflictError("GATHERING_NOT_RECURRABLE", "只有已完成的局可结束复局选择")
        existing = db.scalar(
            select(GatheringRecurrenceDecision).where(
                GatheringRecurrenceDecision.gathering_id == gathering_id,
                GatheringRecurrenceDecision.user_id == user_id,
            )
        )
        if existing is None:
            db.add(
                GatheringRecurrenceDecision(
                    gathering_id=gathering_id,
                    user_id=user_id,
                    decision="ended",
                    kept_user_ids=[],
                )
            )
            db.commit()
        return {"gathering_id": gathering_id, "decision": "ended", "notified": False}


_SHANGHAI = ZoneInfo("Asia/Shanghai")
_WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _format_local_slot(start_at: datetime | None, end_at: datetime | None) -> str | None:
    if start_at is None:
        return None
    local_start = ensure_utc(start_at).astimezone(_SHANGHAI)
    text = f"{_WEEKDAY_LABELS[local_start.weekday()]} {local_start.strftime('%H:%M')}"
    if end_at is not None:
        local_end = ensure_utc(end_at).astimezone(_SHANGHAI)
        text += f"-{local_end.strftime('%H:%M')}"
    return text


def icebreaker_view(db: Session, gathering_id: str, user_id: str) -> dict:
    """成局后 30 秒的破冰包：为什么是你们 / 第一句怎么开 / 下一步是什么。

    只读既有事实（课程重合、兴趣画像、角色互补、历史同局），
    永不发明评价字段；仅在身份披露后对成员可见。
    """

    gathering = get_gathering(db, gathering_id)
    require_member(db, gathering_id, user_id)
    if gathering.status not in IDENTITY_VISIBLE_STATES:
        raise ConflictError("ICEBREAKER_NOT_READY", "破冰内容会在全员确认后解锁")
    members = active_members(db, gathering_id)
    member_ids = [item.user_id for item in members]

    from onemore.db.models import Course, Enrollment, Relation, SharedExperience
    from onemore.modules.taste_profile.service import public_interest_tags

    facts: list[dict[str, str]] = []

    # 同班课程：按教学班聚合，出现 >=2 名成员即为可说出口的共同点。
    rows = db.execute(
        select(Course.name, Enrollment.class_code, Enrollment.user_id).join(
            Enrollment, Enrollment.course_id == Course.id
        ).where(Enrollment.user_id.in_(member_ids))
    ).all()
    class_members: dict[str, set[str]] = {}
    class_course: dict[str, str] = {}
    for course_name, class_code, enrolled_id in rows:
        class_members.setdefault(class_code, set()).add(enrolled_id)
        class_course[class_code] = course_name
    shared_courses: list[tuple[str, int]] = sorted(
        (
            (class_course[code], len(ids))
            for code, ids in class_members.items()
            if len(ids) >= 2
        ),
        key=lambda item: (-item[1], item[0]),
    )
    for course_name, count in shared_courses[:2]:
        scope = "你们都" if count == len(member_ids) else f"你们中有 {count} 人"
        facts.append({"kind": "common_course", "text": f"{scope}在上《{course_name}》"})

    # 兴趣画像重合：只用本人公开的兴趣 chips。
    tag_counts: dict[str, int] = {}
    for item_id in member_ids:
        for tag in public_interest_tags(db, item_id):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    shared_tags = sorted(
        ((tag, count) for tag, count in tag_counts.items() if count >= 2),
        key=lambda item: (-item[1], item[0]),
    )
    for tag, count in shared_tags[:2]:
        scope = "都" if count == len(member_ids) else f"{count} 人都"
        facts.append({"kind": "common_interest", "text": f"你们{scope}对「{tag}」感兴趣"})

    # 角色互补：互补局里各自认领的角色是现成的开场白。
    roles = [item.role for item in members if item.role]
    if gathering.mode == "complementary" and len(roles) >= 2:
        facts.append(
            {"kind": "role_complement", "text": f"角色已就位：{' × '.join(dict.fromkeys(roles))}"}
        )

    # 跨院系：主动跨域是这个产品独有的人格信号。
    colleges = {
        college
        for item_id in member_ids
        if (user := db.get(User, item_id)) is not None
        and (college := (user.college or "").strip())
    }
    if len(colleges) >= 2:
        facts.append({"kind": "cross_college", "text": f"这是一次跨院系组队（{len(colleges)} 个院系）"})

    # 历史同局：真实的共同经历计数。
    prior = 0
    for index, left in enumerate(sorted(member_ids)):
        for right in sorted(member_ids)[index + 1 :]:
            relation = db.scalar(
                select(Relation).where(
                    Relation.participant_a_id == left,
                    Relation.participant_b_id == right,
                )
            )
            if relation is not None:
                prior += (
                    db.scalar(
                        select(func.count(SharedExperience.id)).where(
                            SharedExperience.relation_id == relation.id
                        )
                    )
                    or 0
                )
    if prior:
        facts.append({"kind": "prior_experience", "text": f"你们之间已经有 {prior} 段共同经历"})

    slot = _format_local_slot(gathering.start_at, gathering.end_at)
    if slot:
        facts.append({"kind": "time_match", "text": f"大家都空出了{slot}"})

    # 第一句话模板：可选、不强制，让开口不尴尬。
    first_lines: list[str] = []
    if shared_courses:
        first_lines.append(f"听说都在上《{shared_courses[0][0]}》，你们是哪个班的？")
    if shared_tags:
        first_lines.append(f"看到共同点里有「{shared_tags[0][0]}」，果然是同类")
    if gathering.mode == "complementary" and roles:
        first_lines.append("各自报一下最擅长的部分吧，分工立刻就清楚了")
    if not first_lines:
        first_lines.append(f"我是冲着「{gathering.goal[:20]}」来的，你们呢？")
    first_lines = first_lines[:3]

    checklist: list[str] = []
    if slot:
        checklist.append(f"时间：{slot}")
    checklist.append(
        f"地点：{gathering.location}" if gathering.location else "还没定地点，先在群里定个碰头点"
    )
    if gathering.required_roles:
        role_labels = _looking_for_labels(db, gathering.required_roles)
        if role_labels:
            checklist.append(f"待认领角色：{'、'.join(role_labels)}")

    return {
        "gathering_id": gathering.id,
        "headline": gathering.match_reason or "时间对上了，目标一致，就差认识一下",
        "facts": facts,
        "first_lines": first_lines,
        "next_steps": {
            "start_at": gathering.start_at,
            "end_at": gathering.end_at,
            "location": gathering.location,
            "campus": gathering.campus,
            "channel_id": _channel_id(db, gathering.id),
            "checklist": checklist,
        },
    }


def _semester_start(now_local: datetime) -> datetime:
    if now_local.month >= 8:
        anchor = now_local.replace(month=8, day=1)
    elif now_local.month >= 2:
        anchor = now_local.replace(month=2, day=1)
    else:
        anchor = now_local.replace(year=now_local.year - 1, month=8, day=1)
    return anchor.replace(hour=0, minute=0, second=0, microsecond=0)


def semester_recap(db: Session, user_id: str) -> dict:
    """学期成局回忆录：服务端纯事实聚合，天然可分享（分享文案不含他人身份）。"""

    now_local = datetime.now(UTC).astimezone(_SHANGHAI)
    since = _semester_start(now_local).astimezone(UTC)
    completed_states = [
        GatheringStatus.COMPLETED.value,
        GatheringStatus.RECURRENCE_PENDING.value,
        GatheringStatus.ARCHIVED.value,
    ]
    rows = db.execute(
        select(Gathering)
        .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
        .where(
            GatheringMember.user_id == user_id,
            GatheringMember.completion_confirmed.is_(True),
            Gathering.status.in_(completed_states),
            Gathering.completed_at.is_not(None),
            Gathering.completed_at >= since,
        )
        .order_by(Gathering.completed_at)
    ).scalars()
    gatherings = list(rows)

    total_minutes = 0
    type_counts: dict[str, int] = {}
    location_counts: dict[str, int] = {}
    partner_counts: dict[str, int] = {}
    for gathering in gatherings:
        if gathering.start_at is not None and gathering.end_at is not None:
            total_minutes += int(
                (ensure_utc(gathering.end_at) - ensure_utc(gathering.start_at)).total_seconds()
                // 60
            )
        type_counts[gathering.gathering_type] = type_counts.get(gathering.gathering_type, 0) + 1
        if gathering.location:
            location_counts[gathering.location] = location_counts.get(gathering.location, 0) + 1
        for other in active_members(db, gathering.id):
            if other.user_id != user_id and other.completion_confirmed:
                partner_counts[other.user_id] = partner_counts.get(other.user_id, 0) + 1

    top_partner = None
    if partner_counts:
        partner_id, times = max(partner_counts.items(), key=lambda item: (item[1], item[0]))
        partner_user = db.get(User, partner_id)
        if partner_user is not None:
            top_partner = {
                "display_name": partner_user.display_name,
                "times_together": times,
            }

    recurrences = db.scalar(
        select(func.count(TrustEvent.id)).where(
            TrustEvent.user_id == user_id,
            TrustEvent.event_type == "recurred",
            TrustEvent.occurred_at >= since,
        )
    ) or 0

    top_types = sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
    top_location = (
        max(location_counts.items(), key=lambda item: (item[1], item[0]))[0]
        if location_counts
        else None
    )
    total_hours = round(total_minutes / 60, 1)
    term_label = f"{_semester_start(now_local).year} {'秋季' if _semester_start(now_local).month == 8 else '春季'}学期"

    highlights: list[str] = []
    if gatherings:
        highlights.append(f"成了 {len(gatherings)} 局")
    if partner_counts:
        highlights.append(f"遇见 {len(partner_counts)} 位搭子")
    if total_hours:
        highlights.append(f"一起度过 {total_hours} 小时")
    if recurrences:
        highlights.append(f"复局 {recurrences} 次")

    share_text = (
        f"这学期我在噜噜成局成了 {len(gatherings)} 局、"
        f"遇见 {len(partner_counts)} 位搭子，还差一个，就是你。"
        if gatherings
        else "这学期我刚上桌，还差一个，就是你。"
    )

    return {
        "term_label": term_label,
        "since": since,
        "gatherings_completed": len(gatherings),
        "partners_met": len(partner_counts),
        "total_hours": total_hours,
        "recurrences": int(recurrences),
        "top_partner": top_partner,
        "top_types": [{"gathering_type": name, "count": count} for name, count in top_types],
        "top_location": top_location,
        "highlights": highlights,
        "share_text": share_text,
    }


def create_recurring_series(
    db: Session,
    gathering_id: str,
    user_id: str,
    body: RecurringGatheringRequest,
) -> list[Gathering]:
    """Create a T3-only fixed series with an immutable weekly schedule."""

    trust_service.require_unlock(db, user_id, "recurring_gathering")
    original = get_gathering(db, gathering_id)
    require_member(db, gathering_id, user_id)
    if original.owner_user_id != user_id:
        raise ForbiddenError("只有原局发起人可创建周期性固定局")
    if original.status not in {
        GatheringStatus.COMPLETED.value,
        GatheringStatus.RECURRENCE_PENDING.value,
        GatheringStatus.ARCHIVED.value,
    }:
        raise ConflictError("GATHERING_NOT_RECURRABLE", "完成后的局才可创建固定周期")
    existing_decision = db.scalar(
        select(GatheringRecurrenceDecision).where(
            GatheringRecurrenceDecision.gathering_id == original.id,
            GatheringRecurrenceDecision.user_id == user_id,
        )
    )
    if existing_decision is not None:
        raise ConflictError(
            "RECURRENCE_ALREADY_DECIDED",
            "你已完成本次复局选择，不能再创建另一组固定周期",
        )
    first_start = ensure_utc(body.first_start_at)
    now = datetime.now(UTC)
    if first_start <= now:
        raise ConflictError("START_TIME_IN_PAST", "首期开始时间必须晚于当前时间")
    if body.duration_minutes is not None:
        duration = timedelta(minutes=body.duration_minutes)
    elif original.start_at is not None and original.end_at is not None:
        duration = ensure_utc(original.end_at) - ensure_utc(original.start_at)
    else:
        duration = timedelta(minutes=90)
    if duration < timedelta(minutes=30) or duration > timedelta(hours=24):
        raise ConflictError("INVALID_DURATION", "固定局时长需在 30 分钟到 24 小时之间")

    member_ids = [item.user_id for item in active_members(db, original.id)]
    if user_id not in member_ids:
        member_ids.append(user_id)
    member_users = [db.get(User, member_id) for member_id in member_ids]
    if len(member_users) != len(member_ids) or any(
        member is None
        or member.account_status != "active"
        or not member.social_enabled
        or original.min_size < member.minimum_group_size
        for member in member_users
    ):
        raise ConflictError(
            "RECURRING_MEMBER_PRIVACY_CHANGED",
            "成员的社交或最低人数设置已变化，请先重新确认成员范围",
        )
    current_users = [member for member in member_users if member is not None]
    if any(
        users_have_block_between(db, left.id, right.id)
        for index, left in enumerate(current_users)
        for right in current_users[index + 1 :]
    ):
        raise ConflictError(
            "RECURRING_MEMBER_BLOCKED",
            "成员间的安全设置已变化，不能创建固定周期",
        )
    if original.same_gender_only or any(member.same_gender_only for member in current_users):
        genders = {
            (member.gender_code or "").strip().lower() for member in current_users
        }
        if len(genders) != 1 or bool(
            genders.intersection({"", "unknown", "unspecified"})
        ):
            raise ConflictError(
                "RECURRING_MEMBER_PRIVACY_CHANGED",
                "成员的同性偏好已变化，不能创建固定周期",
            )
    if any(
        LEVEL_ORDER[trust_service.ensure_trust_profile(db, member.id).level]
        < LEVEL_ORDER[original.required_trust_level]
        for member in current_users
    ):
        raise ConflictError(
            "RECURRING_MEMBER_TRUST_CHANGED",
            "成员当前信任等级不再满足原局门槛",
        )
    series_id = new_id()
    created: list[Gathering] = []
    for index in range(body.occurrences):
        start_at = first_start + timedelta(weeks=index * body.interval_weeks)
        end_at = start_at + duration
        item = Gathering(
            owner_user_id=user_id,
            gathering_type=original.gathering_type,
            mode=original.mode,
            title=original.title,
            goal=original.goal,
            status=GatheringStatus.POOLING.value,
            min_size=original.min_size,
            target_size=original.target_size,
            required_trust_level=original.required_trust_level,
            campus=original.campus,
            same_gender_only=original.same_gender_only,
            identity_disclosure=original.identity_disclosure,
            start_at=start_at,
            end_at=end_at,
            location=original.location,
            required_roles=original.required_roles,
            official_metadata={
                "created_via": "recurring_gathering",
                "parent_gathering_id": original.id,
                "recurrence": {
                    "series_id": series_id,
                    "rule": f"FREQ=WEEKLY;INTERVAL={body.interval_weeks}",
                    "sequence": index + 1,
                    "occurrences": body.occurrences,
                },
            },
            expires_at=max(now + timedelta(minutes=5), start_at - timedelta(minutes=30)),
        )
        db.add(item)
        db.flush()
        if any(_time_conflict(db, member_id, item) for member_id in member_ids):
            raise ConflictError(
                "RECURRING_TIME_CONFLICT",
                "至少一位成员在固定周期时段已有其他局",
            )
        for member_id in member_ids:
            db.add(
                GatheringMember(
                    gathering_id=item.id,
                    user_id=member_id,
                    joined_via="recurring",
                )
            )
        db.flush()
        if len(member_ids) >= item.min_size:
            transition(db, item, GatheringEvent.MATCHED, actor_user_id=user_id)
            from onemore.modules.notify.service import notify_confirmation_required

            notify_confirmation_required(db, item)
        created.append(item)
    db.add(
        GatheringRecurrenceDecision(
            gathering_id=original.id,
            user_id=user_id,
            decision="series",
            kept_user_ids=member_ids,
            clone_gathering_id=created[0].id if created else None,
        )
    )
    db.commit()
    for item in created:
        db.refresh(item)
    return created


def report_user(
    db: Session,
    gathering_id: str,
    reporter_id: str,
    reported_user_id: str | None,
    reason: str,
    block: bool,
) -> Report:
    gathering = get_gathering(db, gathering_id)
    reporter_record = db.scalar(
        select(GatheringMember).where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.user_id == reporter_id,
        )
    )
    if reporter_record is None:
        raise ForbiddenError("只有本局当前或历史成员可提交安全举报")
    if reported_user_id is not None:
        if reporter_id == reported_user_id:
            raise AppError("INVALID_REPORT", "举报对象不能是本人", 422)
        allowed_ids = {
            item["user_id"]
            for item in _reportable_participants(db, gathering, reporter_id)
        }
        if reported_user_id not in allowed_ids:
            raise ForbiddenError("只能举报曾在本局合法披露给你的成员")
    elif block:
        raise AppError(
            "BLOCK_TARGET_REQUIRED",
            "匿名阶段可举报本局，但拉黑需要选择已披露成员",
            422,
        )
    report = Report(
        reporter_id=reporter_id,
        reported_user_id=reported_user_id,
        gathering_id=gathering_id,
        reason=reason,
    )
    db.add(report)
    if block and reported_user_id is not None:
        exists = db.scalar(
            select(UserBlock).where(
                UserBlock.blocker_id == reporter_id,
                UserBlock.blocked_id == reported_user_id,
            )
        )
        if not exists:
            db.add(UserBlock(blocker_id=reporter_id, blocked_id=reported_user_id))
    db.commit()
    db.refresh(report)
    return report


def resolve_report(db: Session, report_id: str, valid: bool) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("举报", report_id)
    report.status = "valid" if valid else "dismissed"
    if valid and report.reported_user_id is not None:
        trust_service.record_event(db, report.reported_user_id, "valid_report", report.gathering_id)
        from onemore.modules.notify.service import push

        push(
            db,
            report.reported_user_id,
            "trust_level_changed",
            {
                "level": "T1",
                "reason": "已核验的安全举报触发观察期",
                "appeal": "/trust/appeal",
                "screen_id": "M3",
                "deep_link": "onemore://trust/progress",
                "public_badge": False,
            },
        )
        for blocker_id, blocked_id in (
            (report.reporter_id, report.reported_user_id),
            (report.reported_user_id, report.reporter_id),
        ):
            exists = db.scalar(
                select(UserBlock).where(
                    UserBlock.blocker_id == blocker_id,
                    UserBlock.blocked_id == blocked_id,
                )
            )
            if not exists:
                db.add(UserBlock(blocker_id=blocker_id, blocked_id=blocked_id))
    db.commit()
    return report


def dissolve_expired(db: Session) -> int:
    now = datetime.now(UTC)
    gatherings = list(
        db.scalars(
            select(Gathering).where(
                Gathering.status == GatheringStatus.POOLING.value,
                or_(
                    Gathering.expires_at <= now,
                    Gathering.end_at <= now,
                ),
            )
        )
    )
    for gathering in gatherings:
        with gathering_locks.acquire(gathering.id):
            db.refresh(gathering)
            _finalize_expired_locked(db, gathering)
    db.commit()
    return len(gatherings)


def schedule_completion_confirmations(db: Session) -> int:
    now = datetime.now(UTC)
    gatherings = list(
        db.scalars(
            select(Gathering).where(
                Gathering.status.in_(
                    [GatheringStatus.EXECUTED.value, GatheringStatus.ACTIVE.value]
                ),
                Gathering.end_at.is_not(None),
                Gathering.end_at <= now,
            )
        )
    )
    from onemore.modules.notify.service import notify_completion_confirmation

    count = 0
    for gathering in gatherings:
        count += len(notify_completion_confirmation(db, gathering))
    db.commit()
    return count


def adjudicate_overdue_completion_outcomes(db: Session) -> dict[str, int]:
    """Close stale completion prompts without exposing peer attendance claims.

    For T4 official gatherings, organizer check-in is the attendance evidence;
    an absent check-in after a 24-hour grace period produces a no-show.  For
    ordinary groups, silence is recorded as unresolved with zero trust weight—
    only a member's explicit ``completed=false`` can mark their own no-show.
    """

    cutoff = datetime.now(UTC) - timedelta(hours=24)
    gatherings = list(
        db.scalars(
            select(Gathering).where(
                Gathering.status.in_(
                    [GatheringStatus.EXECUTED.value, GatheringStatus.ACTIVE.value]
                ),
                Gathering.end_at.is_not(None),
                Gathering.end_at <= cutoff,
            )
        )
    )
    counts = {"gatherings": 0, "no_shows": 0, "unresolved": 0, "completed": 0}
    for gathering in gatherings:
        with gathering_locks.acquire(gathering.id):
            db.refresh(gathering)
            if gathering.status not in {
                GatheringStatus.EXECUTED.value,
                GatheringStatus.ACTIVE.value,
            }:
                continue
            counts["gatherings"] += 1
            attended_ids = set(
                db.scalars(
                    select(OrganizerAttendance.user_id).where(
                        OrganizerAttendance.gathering_id == gathering.id
                    )
                )
            )
            for member in active_members(db, gathering.id):
                if member.completion_confirmed or _completion_outcome(
                    db, gathering.id, member.user_id
                ):
                    continue
                if gathering.is_official:
                    if member.user_id in attended_ids:
                        member.completion_confirmed = True
                        trust_service.record_event_once(
                            db,
                            member.user_id,
                            "completion_confirmed",
                            gathering.id,
                        )
                    else:
                        trust_service.record_event_once(
                            db, member.user_id, "no_show", gathering.id
                        )
                        counts["no_shows"] += 1
                else:
                    trust_service.record_event_once(
                        db,
                        member.user_id,
                        "completion_unresolved",
                        gathering.id,
                    )
                    counts["unresolved"] += 1
            if _finalize_completion_if_resolved(db, gathering):
                counts["completed"] += 1
            db.commit()
    return counts


def expire_confirmations(db: Session) -> int:
    now = datetime.now(UTC)
    gatherings = list(
        db.scalars(
            select(Gathering).where(
                Gathering.status == GatheringStatus.TENTATIVE.value,
                Gathering.confirmation_deadline.is_not(None),
                Gathering.confirmation_deadline <= now,
            )
        )
    )
    timed_out = 0
    for gathering in gatherings:
        pending = [
            member
            for member in active_members(db, gathering.id)
            if member.confirmation_status != ConfirmationStatus.CONFIRMED.value
        ]
        for member in pending:
            candidate_intent = db.scalar(
                select(IntentCard)
                .where(
                    IntentCard.user_id == member.user_id,
                    IntentCard.gathering_type == gathering.gathering_type,
                    IntentCard.status == IntentStatus.MATCHED.value,
                )
                .order_by(IntentCard.updated_at.desc())
            )
            if candidate_intent:
                candidate_intent.status = IntentStatus.POOLING.value
            db.delete(member)
            timed_out += 1
        transition(db, gathering, GatheringEvent.MEMBER_LEFT)
        db.execute(
            update(GatheringMember)
            .where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.left_at.is_(None),
            )
            .values(confirmation_status=ConfirmationStatus.PENDING.value, confirmed_at=None)
        )
        db.flush()
        remaining = db.scalar(
            select(GatheringMember.id).where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.left_at.is_(None),
            )
        )
        if remaining is None:
            transition(db, gathering, GatheringEvent.DISSOLVE)
            db.execute(delete(GatheringMember).where(GatheringMember.gathering_id == gathering.id))
    db.commit()
    return timed_out


def start_due_gatherings(db: Session) -> int:
    now = datetime.now(UTC)
    gatherings = list(
        db.scalars(
            select(Gathering).where(
                Gathering.status.in_(
                    [
                        GatheringStatus.CONFIRMED.value,
                        GatheringStatus.PREVIEWED.value,
                        GatheringStatus.EXECUTED.value,
                    ]
                ),
                Gathering.start_at.is_not(None),
                Gathering.start_at <= now,
            )
        )
    )
    for gathering in gatherings:
        with gathering_locks.acquire(gathering.id):
            db.refresh(gathering)
            if gathering.status in {
                GatheringStatus.CONFIRMED.value,
                GatheringStatus.PREVIEWED.value,
                GatheringStatus.EXECUTED.value,
            }:
                transition(db, gathering, GatheringEvent.START)
    db.commit()
    return len(gatherings)
