from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from itertools import combinations
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from onemore.core.contact_policy import channel_has_blocked_peer, users_have_block_between
from onemore.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from onemore.core.time import ensure_utc
from onemore.db.models import (
    Channel,
    ChannelParticipant,
    ChannelStatus,
    Course,
    Enrollment,
    Gathering,
    GatheringMember,
    GatheringStatus,
    MediaChannelGrant,
    Message,
    Relation,
    RelationStatus,
    SharedExperience,
    SharedGoal,
    SharedGoalMemberProgress,
    User,
    utcnow,
)
from onemore.modules.collab.schemas import MessageCreate
from onemore.modules.media import service as media_service
from onemore.modules.trust import service as trust_service

CHANNEL_OPEN_STATES = {
    GatheringStatus.CONFIRMED.value,
    GatheringStatus.PREVIEWED.value,
    GatheringStatus.EXECUTED.value,
    GatheringStatus.ACTIVE.value,
    GatheringStatus.COMPLETED.value,
    GatheringStatus.RECURRENCE_PENDING.value,
    GatheringStatus.ARCHIVED.value,
}

SENSITIVE_SCENE_MARKERS = (
    "图书馆自习区",
    "图书馆自习空间",
    "健身房器械区",
    "健身房力量区",
)


def classify_scene_sensitivity(location: str | None) -> str:
    """Map a server-owned venue label to a stable policy category.

    Library seminar rooms remain collaborative; other library zones and all
    explicitly named gym zones fail closed as onsite-muted. This deliberately
    accepts floor/zone wording variants instead of relying on one exact phrase.
    """
    normalized = "".join((location or "").strip().lower().split())
    if not normalized:
        return "social"
    if "图书馆" in normalized and "研讨室" not in normalized:
        return "sensitive_muted_onsite"
    if "健身房" in normalized:
        return "sensitive_muted_onsite"
    if any("".join(marker.lower().split()) in normalized for marker in SENSITIVE_SCENE_MARKERS):
        return "sensitive_muted_onsite"
    return "social"


def channel_scene_policy(db: Session, channel_id: str, user_id: str) -> dict:
    channel = require_channel_member(db, channel_id, user_id)
    if channel.gathering_id is None:
        return {
            "mode": "social",
            "phase": "always",
            "sending_enabled": True,
            "live_connection_enabled": True,
            "reason": None,
            "next_change_at": None,
            "source": "server_scene_policy",
        }
    gathering = db.get(Gathering, channel.gathering_id)
    if gathering is None:
        raise NotFoundError("局", channel.gathering_id)
    sensitivity = classify_scene_sensitivity(gathering.location)
    if sensitivity == "social":
        return {
            "mode": "social",
            "phase": "always",
            "sending_enabled": True,
            "live_connection_enabled": True,
            "reason": None,
            "next_change_at": None,
            "source": "server_scene_policy",
        }
    now = datetime.now(UTC)
    start = ensure_utc(gathering.start_at) if gathering.start_at else None
    end = ensure_utc(gathering.end_at) if gathering.end_at else None
    if start is not None and now < start:
        phase = "pre_arrival"
        enabled = True
        next_change = start
    elif end is not None and now >= end:
        phase = "post_event"
        enabled = True
        next_change = None
    else:
        phase = "onsite_muted"
        enabled = False
        next_change = end
    return {
        "mode": "sensitive_muted_onsite",
        "phase": phase,
        "sending_enabled": enabled,
        "live_connection_enabled": enabled,
        "reason": (
            None
            if enabled
            else "图书馆自习区与健身房器械区现场默认禁言，只在到场前组队、结束后复盘"
        ),
        "next_change_at": next_change,
        "source": "server_scene_policy",
    }


def require_channel_live_access(db: Session, channel_id: str, user_id: str) -> None:
    policy = channel_scene_policy(db, channel_id, user_id)
    if not policy["live_connection_enabled"]:
        raise ConflictError(
            "SCENE_CONNECTION_MUTED",
            policy["reason"],
            {
                "phase": policy["phase"],
                "next_change_at": (
                    ensure_utc(policy["next_change_at"]).isoformat().replace("+00:00", "Z")
                    if policy["next_change_at"]
                    else None
                ),
            },
        )


def require_channel_send_allowed(db: Session, channel_id: str, user_id: str) -> None:
    policy = channel_scene_policy(db, channel_id, user_id)
    if not policy["sending_enabled"]:
        raise ConflictError(
            "SCENE_MUTED_ONSITE",
            policy["reason"],
            {
                "phase": policy["phase"],
                "next_change_at": (
                    ensure_utc(policy["next_change_at"]).isoformat().replace("+00:00", "Z")
                    if policy["next_change_at"]
                    else None
                ),
            },
        )


def _member_ids(db: Session, gathering_id: str) -> list[str]:
    return list(
        db.scalars(
            select(GatheringMember.user_id).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
    )


def open_gathering_channel(db: Session, gathering_id: str) -> Channel:
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    if gathering.status not in CHANNEL_OPEN_STATES:
        raise ConflictError("CHANNEL_NOT_AVAILABLE", "对话仅在全员确认后开启")
    channel = db.scalar(select(Channel).where(Channel.gathering_id == gathering_id))
    if channel is not None:
        if channel.status == ChannelStatus.CLOSED.value:
            current_ids = set(_member_ids(db, gathering_id))
            existing = list(
                db.scalars(
                    select(ChannelParticipant).where(
                        ChannelParticipant.channel_id == channel.id
                    )
                )
            )
            existing_ids = {item.user_id for item in existing}
            db.execute(
                delete(ChannelParticipant).where(
                    ChannelParticipant.channel_id == channel.id,
                    ChannelParticipant.user_id.not_in(current_ids),
                )
            )
            channel.status = ChannelStatus.OPEN.value
            channel.opened_at = utcnow()
            channel.archived_at = None
            for user_id in current_ids - existing_ids:
                # joined_at is the history boundary: replacements can only
                # read messages sent after they joined, while original current
                # members retain the collaboration record they participated in.
                db.add(
                    ChannelParticipant(
                        channel_id=channel.id,
                        user_id=user_id,
                        joined_at=utcnow(),
                    )
                )
            db.flush()
        return channel
    channel = Channel(gathering_id=gathering_id, status=ChannelStatus.OPEN.value)
    db.add(channel)
    db.flush()
    for user_id in _member_ids(db, gathering_id):
        db.add(ChannelParticipant(channel_id=channel.id, user_id=user_id))
    # 入群第一屏：系统一次性塞入成局卡摘要（时间/地点/角色，纯事实），
    # 随后阿凑只说一句开场白，之后除非被 @ 不再出场。
    db.add(
        Message(
            channel_id=channel.id,
            sender_id="system",
            sender_type="system",
            content_type="text",
            content=gathering_summary_card(db, gathering_id),
        )
    )
    opener = generate_opener(db, gathering_id)
    db.add(
        Message(
            channel_id=channel.id,
            sender_id="azou",
            sender_type="azou",
            content_type="text",
            content=opener,
        )
    )
    db.flush()
    return channel


def gathering_summary_card(db: Session, gathering_id: str) -> str:
    """成局卡摘要：进群第一眼看到的事实卡（时间、地点、人、角色）。"""

    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    members = list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
    )
    lines = [f"成局卡 · {gathering.title}"]
    if gathering.start_at is not None:
        local = ensure_utc(gathering.start_at).astimezone(ZoneInfo("Asia/Shanghai"))
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][local.weekday()]
        slot = f"{local.month}月{local.day}日 {weekday} {local:%H:%M}"
        if gathering.end_at is not None:
            slot += f"-{ensure_utc(gathering.end_at).astimezone(ZoneInfo('Asia/Shanghai')):%H:%M}"
        lines.append(f"时间：{slot}")
    lines.append(f"地点：{gathering.location or '待定，先在这里商量'}")
    lines.append(f"人数：{len(members)} 人已就位")
    roles = [member.role for member in members if member.role]
    if roles:
        lines.append(f"分工：{' / '.join(dict.fromkeys(roles))}")
    return "\n".join(lines)


def generate_opener(db: Session, gathering_id: str) -> str:
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    context = recall_for_opener(db, gathering_id)
    common = context.get("common_grounds", [])
    common_text = f"你们的共同点是：{'、'.join(common)}。" if common else "你们有兼容的时间和目标。"
    return f"{common_text}第一次先确认目标、分工与下一步即可。"


def require_channel_member(db: Session, channel_id: str, user_id: str) -> Channel:
    channel = db.get(Channel, channel_id)
    if channel is None:
        raise NotFoundError("对话通道", channel_id)
    membership = db.scalar(
        select(ChannelParticipant.id).where(
            ChannelParticipant.channel_id == channel_id,
            ChannelParticipant.user_id == user_id,
        )
    )
    if membership is None:
        raise ForbiddenError("只有共同完成局的成员可访问该通道")
    if channel.status == ChannelStatus.CLOSED.value:
        raise ConflictError("CHANNEL_CLOSED", "关系已解除，对话通道已关闭")
    if channel_has_blocked_peer(db, channel_id, user_id):
        raise ForbiddenError("拉黑后双方均不可继续访问、发送或接收该会话内容")
    return channel


def authorized_channel_user_ids(db: Session, channel_id: str) -> set[str]:
    candidates = set(
        db.scalars(
            select(ChannelParticipant.user_id).where(
                ChannelParticipant.channel_id == channel_id
            )
        )
    )
    allowed: set[str] = set()
    for candidate in candidates:
        try:
            require_channel_member(db, channel_id, candidate)
            allowed.add(candidate)
        except AppError:
            continue
    return allowed


def send_message(
    db: Session,
    channel_id: str,
    user_id: str,
    content: str,
    content_type: str = "text",
) -> Message:
    require_channel_send_allowed(db, channel_id, user_id)
    message = Message(
        channel_id=channel_id,
        sender_id=user_id,
        sender_type="human",
        content_type=content_type,
        content=content.strip(),
    )
    db.add(message)
    from onemore.modules.notify.service import push

    recipients = list(
        db.scalars(
            select(ChannelParticipant.user_id).where(
                ChannelParticipant.channel_id == channel_id,
                ChannelParticipant.user_id != user_id,
            )
        )
    )
    authorized_recipients = authorized_channel_user_ids(db, channel_id)
    for recipient_id in recipients:
        if (
            recipient_id not in authorized_recipients
            or users_have_block_between(db, user_id, recipient_id)
        ):
            continue
        push(
            db,
            recipient_id,
            "chat_message",
            {
                "channel_id": channel_id,
                "deep_link": f"onemore://channel/{channel_id}",
                "summary": "会话有新消息",
            },
        )
    db.commit()
    db.refresh(message)
    return message


def prepare_message_content(
    db: Session, channel_id: str, user_id: str, body: MessageCreate
) -> str:
    require_channel_send_allowed(db, channel_id, user_id)
    if body.content_type == "text":
        return (body.content or "").strip()
    if body.content_type == "location" and body.location is not None:
        return json.dumps(body.location.model_dump(), ensure_ascii=False, separators=(",", ":"))
    if body.content_type == "image" and body.image is not None:
        asset = media_service.get_authorized_asset(db, body.image.media_id, user_id)
        grant = db.scalar(
            select(MediaChannelGrant).where(
                MediaChannelGrant.media_id == asset.id,
                MediaChannelGrant.channel_id == channel_id,
            )
        )
        if grant is None:
            db.add(MediaChannelGrant(media_id=asset.id, channel_id=channel_id))
            db.flush()
        payload = media_service.asset_view(asset)
        payload["caption"] = body.image.caption
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    raise AppError("MESSAGE_PAYLOAD_INVALID", "消息载荷无效", 422)


def message_view_data(message: Message) -> dict:
    data = {
        "id": message.id,
        "channel_id": message.channel_id,
        "sender_id": message.sender_id,
        "sender_type": message.sender_type,
        "content_type": message.content_type,
        "content": None,
        "image": None,
        "location": None,
        "sent_at": message.sent_at,
    }
    if message.content_type == "text":
        data["content"] = message.content
    else:
        try:
            data[message.content_type] = json.loads(message.content)
        except json.JSONDecodeError:
            data["content"] = message.content
    return data


def list_messages(
    db: Session,
    channel_id: str,
    user_id: str,
    *,
    before: datetime | None = None,
    limit: int = 50,
) -> list[Message]:
    require_channel_member(db, channel_id, user_id)
    membership = db.scalar(
        select(ChannelParticipant).where(
            ChannelParticipant.channel_id == channel_id,
            ChannelParticipant.user_id == user_id,
        )
    )
    if membership is None:
        raise ForbiddenError("只有当前通道成员可读取消息")
    query = select(Message).where(
        Message.channel_id == channel_id,
        Message.sent_at >= membership.joined_at,
    )
    if before:
        query = query.where(Message.sent_at < before)
    items = list(db.scalars(query.order_by(Message.sent_at.desc()).limit(limit)))
    return list(reversed(items))


def mention_azou(
    db: Session, channel_id: str, user_id: str, text: str
) -> tuple[Message, dict | None]:
    require_channel_send_allowed(db, channel_id, user_id)
    lowered = text.lower()
    hint: dict | None = None
    if any(word in lowered for word in ("改时间", "改约", "空档")):
        hint = {"type": "open_reschedule", "channel_id": channel_id}
        response = "我已整理改约入口；候选时间只展示共同交集，不会暴露任何人的课表。"
    elif any(word in lowered for word in ("场地", "研讨室", "羽毛球")):
        hint = {"type": "open_action_preview", "channel_id": channel_id}
        response = "我已准备场地查询入口；真实提交前仍会先给全员看预览。"
    elif any(word in lowered for word in ("日历", "提醒")):
        hint = {"type": "calendar", "channel_id": channel_id}
        response = "我已准备日历入口；只有执行成功的局才会生成日历事件。"
    else:
        response = "我只处理本局的提醒、改约、补位和被点名的工具操作。"
    message = Message(
        channel_id=channel_id,
        sender_id="azou",
        sender_type="azou",
        content_type="text",
        content=response,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message, hint


def exit_protocol(db: Session, gathering_id: str) -> Message:
    channel = open_gathering_channel(db, gathering_id)
    existing = db.scalar(
        select(Message).where(
            Message.channel_id == channel.id,
            Message.sender_type == "azou",
            Message.content.like("%剩下的交给你们%"),
        )
    )
    if existing:
        return existing
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    message = Message(
        channel_id=channel.id,
        sender_id="azou",
        sender_type="azou",
        content_type="text",
        content=(
            f"{gathering.location or '集合地点'}已确认。第一次建议先确认目标和分工。"
            "剩下的交给你们，我只在提醒、改约、补位或被 @ 时再出现。"
        ),
    )
    db.add(message)
    db.flush()
    return message


def measure_exit_success(db: Session, gathering_id: str) -> bool:
    channel = db.scalar(select(Channel).where(Channel.gathering_id == gathering_id))
    if channel is None:
        return False
    cutoff = channel.opened_at + timedelta(hours=24)
    senders = set(
        db.scalars(
            select(Message.sender_id).where(
                Message.channel_id == channel.id,
                Message.sender_type == "human",
                Message.sent_at <= cutoff,
            )
        )
    )
    return len(senders) >= 2


def _common_grounds(db: Session, user_a: str, user_b: str) -> list[str]:
    rows = db.execute(
        select(Course.name, Enrollment.class_code)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.user_id.in_([user_a, user_b]))
    ).all()
    by_class: dict[str, list[str]] = {}
    for course_name, class_code in rows:
        by_class.setdefault(class_code, []).append(course_name)
    return [f"同上《{names[0]}》" for names in by_class.values() if len(names) >= 2][:5]


def record_experience(db: Session, gathering_id: str) -> list[SharedExperience]:
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    if gathering.status != GatheringStatus.COMPLETED.value:
        raise ConflictError("EXPERIENCE_NOT_READY", "共同经历只在局完成时自动沉淀")
    user_ids = sorted(
        db.scalars(
            select(GatheringMember.user_id).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
                GatheringMember.completion_confirmed.is_(True),
            )
        )
    )
    output: list[SharedExperience] = []
    for user_a, user_b in combinations(user_ids, 2):
        relation = db.scalar(
            select(Relation).where(
                Relation.participant_a_id == user_a,
                Relation.participant_b_id == user_b,
            )
        )
        if relation is None:
            relation = Relation(
                participant_a_id=user_a,
                participant_b_id=user_b,
                created_from_gathering_id=gathering_id,
            )
            db.add(relation)
            db.flush()
            from onemore.modules.notify.service import notify_relation_ready

            notify_relation_ready(db, relation.id, (user_a, user_b))
        else:
            relation.status = RelationStatus.ACTIVE.value
            relation.dissolved_at = None
            relation.dissolved_by = None
        experience = db.scalar(
            select(SharedExperience).where(
                SharedExperience.relation_id == relation.id,
                SharedExperience.gathering_id == gathering_id,
            )
        )
        if experience is None:
            experience = SharedExperience(
                relation_id=relation.id,
                gathering_id=gathering_id,
                participants=[user_a, user_b],
                gathering_type=gathering.gathering_type,
                occurred_at=gathering.completed_at or utcnow(),
                outcome="completed",
                common_grounds=_common_grounds(db, user_a, user_b),
            )
            db.add(experience)
            output.append(experience)
        relation_channel = db.scalar(select(Channel).where(Channel.relation_id == relation.id))
        if relation_channel is None:
            relation_channel = Channel(relation_id=relation.id, status=ChannelStatus.OPEN.value)
            db.add(relation_channel)
            db.flush()
            db.add_all(
                [
                    ChannelParticipant(channel_id=relation_channel.id, user_id=user_a),
                    ChannelParticipant(channel_id=relation_channel.id, user_id=user_b),
                ]
            )
        else:
            # A new jointly completed gathering is the only event that may
            # reactivate a silently dissolved relation. Keep the relation and
            # its channel state atomic so an "active" relation never exposes a
            # permanently closed channel identifier.
            relation_channel.status = ChannelStatus.OPEN.value
            relation_channel.archived_at = None
    db.flush()
    return output


def _relation_or_404(db: Session, relation_id: str, user_id: str) -> Relation:
    relation = db.get(Relation, relation_id)
    if relation is None or relation.status != RelationStatus.ACTIVE.value:
        raise NotFoundError("搭子关系", relation_id)
    if user_id not in {relation.participant_a_id, relation.participant_b_id}:
        raise ForbiddenError()
    return relation


_MILESTONE_STEPS = (1, 3, 5, 10, 20)
_MILESTONE_LABELS = {
    1: "第一次搭档",
    3: "三局之约",
    5: "五局老搭子",
    10: "十局搭子星",
    20: "二十局传说",
}


def _partner_title(times_together: int, recur_count: int) -> str:
    if recur_count >= 2:
        return "固定搭子"
    if times_together >= 5:
        return "老搭子"
    if times_together >= 3:
        return "熟搭子"
    return "新搭子"


def _relation_milestone(times_together: int) -> dict:
    reached = max((step for step in _MILESTONE_STEPS if step <= times_together), default=0)
    upcoming = next((step for step in _MILESTONE_STEPS if step > times_together), None)
    return {
        "reached": reached,
        "reached_label": _MILESTONE_LABELS.get(reached),
        "next": upcoming,
        "next_label": _MILESTONE_LABELS.get(upcoming) if upcoming else None,
        "remaining": (upcoming - times_together) if upcoming else None,
    }


def relation_view(db: Session, relation: Relation, *, include_insights: bool = False) -> dict:
    experiences = list(
        db.scalars(
            select(SharedExperience)
            .where(SharedExperience.relation_id == relation.id)
            .order_by(SharedExperience.occurred_at.desc())
        )
    )
    from onemore.db.models import TasteProfile
    from onemore.modules.taste_profile.service import public_interest_tags

    participants = []
    for user_id in (relation.participant_a_id, relation.participant_b_id):
        user = db.get(User, user_id)
        taste = db.get(TasteProfile, user_id)
        participants.append(
            {
                "user_id": user_id,
                "display_name": user.display_name if user else None,
                "college": user.college if user else None,
                "major": user.major if user else None,
                "interest_tags": public_interest_tags(db, user_id),
                "taste_summary": (taste.summary if taste else None) or None,
            }
        )
    channel_id = db.scalar(select(Channel.id).where(Channel.relation_id == relation.id))

    # 强展示层：把「后台日志」翻译成「关系的物证」，全部来自既有事实。
    timeline: list[dict] = []
    recur_count = 0
    for experience in experiences:
        gathering = db.get(Gathering, experience.gathering_id)
        via_recurrence = bool(
            gathering is not None
            and (gathering.official_metadata or {}).get("created_via") == "recurrence_choice"
        )
        recur_count += int(via_recurrence)
        duration_minutes = None
        location = None
        title = None
        if gathering is not None:
            title = gathering.title
            location = gathering.location
            if gathering.start_at is not None and gathering.end_at is not None:
                duration_minutes = int(
                    (
                        ensure_utc(gathering.end_at) - ensure_utc(gathering.start_at)
                    ).total_seconds()
                    // 60
                )
        timeline.append(
            {
                "gathering_id": experience.gathering_id,
                "title": title,
                "gathering_type": experience.gathering_type,
                "occurred_at": experience.occurred_at,
                "location": location,
                "duration_minutes": duration_minutes,
                "outcome": experience.outcome,
                "common_grounds": experience.common_grounds,
                "via_recurrence": via_recurrence,
            }
        )
    times_together = len(experiences)

    view = {
        "id": relation.id,
        "participants": participants,
        "status": relation.status,
        "experiences": experiences,
        "latest_experience_at": experiences[0].occurred_at if experiences else None,
        "channel_id": channel_id,
        "times_together": times_together,
        "recur_count": recur_count,
        "is_fixed_partner": recur_count >= 2,
        "partner_title": _partner_title(times_together, recur_count),
        "milestone": _relation_milestone(times_together),
        "timeline": timeline,
    }

    if include_insights:
        from onemore.modules.schedule.service import intersect_windows

        now = datetime.now(UTC)
        windows = intersect_windows(
            db,
            [relation.participant_a_id, relation.participant_b_id],
            start_after=now,
            end_before=now + timedelta(days=7),
            minimum_minutes=60,
        )
        view["next_window"] = (
            {"start_at": windows[0].start_at, "end_at": windows[0].end_at}
            if windows
            else None
        )
        goal = db.scalar(
            select(SharedGoal)
            .where(SharedGoal.relation_id == relation.id, SharedGoal.status == "active")
            .order_by(SharedGoal.created_at.desc())
        )
        view["active_goal"] = (
            {
                "id": goal.id,
                "definition": goal.definition,
                "current_value": goal.current_value,
                "target_value": goal.target_value,
                "unit": goal.unit,
                "period_end": goal.period_end,
            }
            if goal is not None
            else None
        )
    return view


def list_relations(db: Session, user_id: str) -> list[dict]:
    relations = list(
        db.scalars(
            select(Relation).where(
                Relation.status == RelationStatus.ACTIVE.value,
                or_(Relation.participant_a_id == user_id, Relation.participant_b_id == user_id),
            )
        )
    )
    views = [relation_view(db, relation) for relation in relations]
    return sorted(
        views,
        key=lambda item: (
            ensure_utc(item["latest_experience_at"])
            if item["latest_experience_at"]
            else datetime.min.replace(tzinfo=UTC)
        ),
        reverse=True,
    )


def get_relation(db: Session, relation_id: str, user_id: str) -> dict:
    return relation_view(db, _relation_or_404(db, relation_id, user_id), include_insights=True)


def dissolve_relation(db: Session, relation_id: str, user_id: str) -> None:
    relation = _relation_or_404(db, relation_id, user_id)
    relation.status = RelationStatus.DISSOLVED.value
    relation.dissolved_by = user_id
    relation.dissolved_at = utcnow()
    channel = db.scalar(select(Channel).where(Channel.relation_id == relation_id))
    if channel:
        channel.status = ChannelStatus.CLOSED.value
    db.commit()


def recall_for_intent(db: Session, user_id: str, intent: dict) -> list[dict]:
    gathering_type = intent.get("gathering_type")
    if not gathering_type:
        return []
    output = []
    for relation in list_relations(db, user_id):
        matching = [
            item for item in relation["experiences"] if item.gathering_type == gathering_type
        ]
        if matching:
            output.append(
                {
                    "relation_id": relation["id"],
                    "participants": relation["participants"],
                    "relevant_experience": matching[0].gathering_type,
                }
            )
    return output


def recall_for_opener(db: Session, gathering_id: str) -> dict:
    member_ids = _member_ids(db, gathering_id)
    common: list[str] = []
    prior_count = 0
    for user_a, user_b in combinations(sorted(member_ids), 2):
        common.extend(_common_grounds(db, user_a, user_b))
        relation = db.scalar(
            select(Relation).where(
                Relation.participant_a_id == user_a,
                Relation.participant_b_id == user_b,
            )
        )
        if relation:
            prior_count += (
                db.scalar(
                    select(func.count(SharedExperience.id)).where(
                        SharedExperience.relation_id == relation.id
                    )
                )
                or 0
            )
    if prior_count:
        common.append(f"成员之间已有 {prior_count} 段共同经历")
    return {"gathering_id": gathering_id, "common_grounds": sorted(set(common))[:6]}


def recall_for_goal(db: Session, goal_id: str) -> dict:
    goal = db.get(SharedGoal, goal_id)
    if goal is None:
        raise NotFoundError("共同目标", goal_id)
    return {
        "goal_id": goal.id,
        "definition": goal.definition,
        "progress": goal.current_value,
        "target": goal.target_value,
        "unit": goal.unit,
    }


def create_goal(
    db: Session,
    relation_id: str,
    user_id: str,
    *,
    definition: str,
    period_start,
    period_end,
    target_value: float,
    unit: str,
) -> SharedGoal:
    _relation_or_404(db, relation_id, user_id)
    trust_service.require_unlock(db, user_id, "shared_goal")
    goal = SharedGoal(
        relation_id=relation_id,
        definition=definition,
        period_start=period_start,
        period_end=period_end,
        target_value=target_value,
        unit=unit,
        milestones=[
            {
                "fraction": fraction,
                "target_value": round(target_value * fraction, 2),
                "reached": False,
                "reached_at": None,
            }
            for fraction in (0.25, 0.5, 0.75, 1.0)
        ],
        next_action="完成下一次预约或到场后，系统会自动记入进度",
    )
    db.add(goal)
    db.flush()
    relation = _relation_or_404(db, relation_id, user_id)
    for member_id in (relation.participant_a_id, relation.participant_b_id):
        db.add(
            SharedGoalMemberProgress(
                goal_id=goal.id,
                user_id=member_id,
            )
        )
    db.commit()
    db.refresh(goal)
    return goal


def list_goals(db: Session, relation_id: str, user_id: str) -> list[SharedGoal]:
    _relation_or_404(db, relation_id, user_id)
    return list(
        db.scalars(
            select(SharedGoal)
            .where(SharedGoal.relation_id == relation_id)
            .order_by(SharedGoal.period_end.desc(), SharedGoal.created_at.desc())
        )
    )


def get_goal(db: Session, goal_id: str, user_id: str) -> SharedGoal:
    goal = db.get(SharedGoal, goal_id)
    if goal is None:
        raise NotFoundError("共同目标", goal_id)
    _relation_or_404(db, goal.relation_id, user_id)
    return goal


def shared_goal_view(db: Session, goal: SharedGoal) -> dict:
    rows = list(
        db.scalars(
            select(SharedGoalMemberProgress)
            .where(SharedGoalMemberProgress.goal_id == goal.id)
            .order_by(SharedGoalMemberProgress.created_at)
        )
    )
    member_progress = []
    for row in rows:
        user = db.get(User, row.user_id)
        member_progress.append(
            {
                "user_id": row.user_id,
                "display_name": user.display_name if user else None,
                "current_value": row.current_value,
                "last_progress_at": row.last_progress_at,
            }
        )
    return {
        "id": goal.id,
        "relation_id": goal.relation_id,
        "definition": goal.definition,
        "period_start": goal.period_start,
        "period_end": goal.period_end,
        "target_value": goal.target_value,
        "current_value": goal.current_value,
        "unit": goal.unit,
        "status": goal.status,
        "milestones": goal.milestones or [],
        "member_progress": member_progress,
        "next_action": goal.next_action,
        "last_broadcast": goal.last_broadcast,
        "last_progress_at": goal.last_progress_at,
        "progress_source": "attendance_and_completion",
    }


def update_goal_next_action(
    db: Session, goal_id: str, user_id: str, next_action: str
) -> SharedGoal:
    goal = db.get(SharedGoal, goal_id)
    if goal is None:
        raise NotFoundError("共同目标", goal_id)
    _relation_or_404(db, goal.relation_id, user_id)
    goal.next_action = next_action
    db.commit()
    db.refresh(goal)
    return goal


def _recompute_goal_progress(db: Session, goal: SharedGoal) -> bool:
    rows = list(
        db.scalars(
            select(SharedGoalMemberProgress).where(
                SharedGoalMemberProgress.goal_id == goal.id
            )
        )
    )
    if not rows:
        return False
    previous = goal.current_value
    goal.current_value = min(
        goal.target_value,
        min(row.current_value for row in rows),
    )
    now = utcnow()
    milestones = []
    for raw in goal.milestones or []:
        item = dict(raw)
        reached = goal.current_value >= float(item["target_value"])
        item["reached"] = reached
        if reached and not item.get("reached_at"):
            item["reached_at"] = now.isoformat()
        milestones.append(item)
    goal.milestones = milestones
    goal.status = "completed" if goal.current_value >= goal.target_value else "active"
    goal.last_progress_at = max(
        (row.last_progress_at for row in rows if row.last_progress_at is not None),
        default=goal.last_progress_at,
    )
    changed = goal.current_value > previous
    if changed:
        if goal.status == "completed":
            goal.next_action = "目标已完成，成员可以在搭子会话中决定是否开启下一阶段"
            goal.last_broadcast = (
                f"共同目标已完成：{goal.current_value:g}/{goal.target_value:g} {goal.unit}"
            )
        else:
            goal.next_action = "确认下一次预约或到场安排"
            goal.last_broadcast = (
                f"已根据到场记录自动更新：{goal.current_value:g}/"
                f"{goal.target_value:g} {goal.unit}"
            )
        relation = db.get(Relation, goal.relation_id)
        if relation is not None:
            from onemore.modules.notify.service import push

            for member_id in (relation.participant_a_id, relation.participant_b_id):
                push(
                    db,
                    member_id,
                    "shared_goal_progress",
                    {
                        "goal_id": goal.id,
                        "relation_id": relation.id,
                        "summary": goal.last_broadcast,
                        "deep_link": f"onemore://goal/{relation.id}",
                    },
                    dedupe_key=(
                        f"shared-goal-progress:{goal.id}:{goal.current_value:g}"
                    ),
                )
    return changed


def record_goal_member_progress(
    db: Session,
    gathering_id: str,
    user_id: str,
    *,
    source: str = "completion",
) -> int:
    """Apply one idempotent participation fact to related goals.

    Check-in and self-completion are two observations of the same gathering,
    not two goal units.  ``source`` remains an audit-facing call-site label,
    while the persisted identity is deliberately gathering-scoped.
    """

    _ = source

    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    member_ids = set(
        db.scalars(
            select(GatheringMember.user_id).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
    )
    if user_id not in member_ids:
        return 0
    relations = list(
        db.scalars(
            select(Relation).where(
                Relation.status == RelationStatus.ACTIVE.value,
                or_(
                    Relation.participant_a_id == user_id,
                    Relation.participant_b_id == user_id,
                ),
            )
        )
    )
    today = datetime.now(UTC).date()
    updated = 0
    touched_goal_ids: set[str] = set()
    for relation in relations:
        partner_id = (
            relation.participant_b_id
            if relation.participant_a_id == user_id
            else relation.participant_a_id
        )
        if partner_id not in member_ids:
            continue
        goals = list(
            db.scalars(
                select(SharedGoal).where(
                    SharedGoal.relation_id == relation.id,
                    SharedGoal.status == "active",
                    SharedGoal.period_start <= today,
                    SharedGoal.period_end >= today,
                )
            )
        )
        for goal in goals:
            progress = db.scalar(
                select(SharedGoalMemberProgress).where(
                    SharedGoalMemberProgress.goal_id == goal.id,
                    SharedGoalMemberProgress.user_id == user_id,
                )
            )
            if progress is None:
                progress = SharedGoalMemberProgress(goal_id=goal.id, user_id=user_id)
                db.add(progress)
                db.flush()
            source_id = f"gathering:{gathering_id}"
            source_ids = list(progress.source_ids or [])
            if source_id in source_ids:
                continue
            source_ids.append(source_id)
            progress.source_ids = source_ids
            progress.current_value = min(goal.target_value, progress.current_value + 1)
            progress.last_progress_at = utcnow()
            _recompute_goal_progress(db, goal)
            touched_goal_ids.add(goal.id)
            updated += 1
    if touched_goal_ids:
        evaluate_goal_reminders(db, goal_ids=touched_goal_ids)
    return updated


def evaluate_goal_reminders(
    db: Session, *, goal_ids: set[str] | None = None
) -> int:
    """Nudge peers of a lagging member, never the lagging member themself."""

    today = datetime.now(UTC).date()
    query = select(SharedGoal).where(
        SharedGoal.status == "active",
        SharedGoal.period_start <= today,
        SharedGoal.period_end >= today,
    )
    if goal_ids is not None:
        query = query.where(SharedGoal.id.in_(goal_ids))
    sent = 0
    from onemore.modules.notify.service import push

    for goal in db.scalars(query):
        total_days = max(1, (goal.period_end - goal.period_start).days)
        elapsed_days = max(0, (today - goal.period_start).days)
        if elapsed_days / total_days < 0.5:
            continue
        expected = goal.target_value * min(1.0, elapsed_days / total_days)
        rows = list(
            db.scalars(
                select(SharedGoalMemberProgress).where(
                    SharedGoalMemberProgress.goal_id == goal.id
                )
            )
        )
        for lagging in [row for row in rows if row.current_value + 0.5 < expected]:
            for recipient in [row for row in rows if row.user_id != lagging.user_id]:
                push(
                    db,
                    recipient.user_id,
                    "shared_goal_peer_support",
                    {
                        "goal_id": goal.id,
                        "relation_id": goal.relation_id,
                        "summary": "共同目标有一位成员暂时低于本期节奏，可以一起确认下一次行动。",
                        "deep_link": f"onemore://goal/{goal.relation_id}",
                    },
                    dedupe_key=(
                        f"shared-goal-support:{goal.id}:{lagging.user_id}:"
                        f"{today.isocalendar().year}-{today.isocalendar().week}"
                    ),
                )
                sent += 1
    return sent


def archive_spaces(db: Session) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=7)
    channels = list(
        db.scalars(
            select(Channel)
            .join(Gathering, Gathering.id == Channel.gathering_id)
            .where(
                Channel.gathering_id.is_not(None),
                Channel.status == ChannelStatus.OPEN.value,
                Gathering.completed_at <= cutoff,
            )
        )
    )
    for channel in channels:
        channel.status = ChannelStatus.ARCHIVED.value
        channel.archived_at = utcnow()
    db.commit()
    return len(channels)
