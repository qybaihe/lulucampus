"""Shared course / gym overlap for Hermes peer matching demos.

Cast users keep their own majors, but many also take 机器学习 / 人工智能伦理 /
体育选修羽毛球, and several hold the same 南校园羽毛球 evening slot. A subset
also holds tonight's 珠海校区篮球 slot so Hermes gym-peer demos can fire.
Live test phones (e.g. 15522668322) can be attached to the same template
without overwriting display name.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.time import ensure_utc

from onemore.db.demo_cast import (
    CAST_BY_ID,
    CAST_TASTE,
    CAST_USERS,
    CHEN,
    COURSE_MEETINGS,
    HE,
    LIANG,
    LIN,
    LIVE_TEST_PHONES,
    PEER_OVERLAP_BASKETBALL,
    PEER_OVERLAP_COURSE_CODES,
    PEER_OVERLAP_GYM,
    CastGymSlot,
)
from onemore.db.models import (
    CampusAction,
    Channel,
    ChannelParticipant,
    ChannelStatus,
    ConfirmationStatus,
    Course,
    Enrollment,
    Gathering,
    GatheringMember,
    GatheringStatus,
    Message,
    Relation,
    TasteImportSession,
    TasteProfile,
    User,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")


def overlap_dates(slot: CastGymSlot):
    today = datetime.now(SHANGHAI).date()
    return [today + timedelta(days=offset) for offset in slot.days_ahead]


def ensure_enrollment(db: Session, user_id: str, course_code: str) -> None:
    course = db.scalar(select(Course).where(Course.code == course_code))
    if course is None:
        return
    class_code = f"{course_code}-01"
    exists = db.scalar(
        select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course.id,
            Enrollment.class_code == class_code,
            Enrollment.term == "2026-fall",
        )
    )
    if exists is not None:
        exists.status = "current"
        return
    now = datetime.now(UTC)
    location, hour = COURSE_MEETINGS.get(course_code, ("校园教学楼", 10))
    start = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
    db.add(
        Enrollment(
            user_id=user_id,
            course_id=course.id,
            class_code=class_code,
            term="2026-fall",
            status="current",
            course_type=course.course_type,
            meeting_windows=[
                {
                    "week": max(1, int(now.strftime("%W")) % 25),
                    "start_at": start.isoformat(),
                    "end_at": (start + timedelta(hours=2)).isoformat(),
                    "location": location,
                }
            ],
        )
    )


def ensure_gym_slots(db: Session, user_id: str, slot: CastGymSlot) -> None:
    for day in overlap_dates(slot):
        key = f"cast-gym-{user_id}-{slot.venue_type}-{day.isoformat()}-{slot.start}"
        existing = db.scalar(select(CampusAction).where(CampusAction.idempotency_key == key))
        params = {
            "venue_type": slot.venue_type,
            "date": day.isoformat(),
            "start": slot.start,
            "end": slot.end,
            "venue": slot.venue,
        }
        if existing is None:
            db.add(
                CampusAction(
                    user_id=user_id,
                    action_name="gym.book_preview",
                    params=params,
                    preview_snapshot={"source": "peer_overlap_template", "params": params},
                    snapshot_hash=key[:64],
                    idempotency_key=key,
                )
            )
        else:
            existing.params = params
            existing.action_name = "gym.book_preview"


def seed_cast_gym_slots(db: Session) -> None:
    for spec in CAST_USERS:
        for slot in spec.gym_slots:
            ensure_gym_slots(db, spec.id, slot)
    db.commit()


def copy_persona_taste(db: Session, user_id: str, persona_id: str = LIN) -> None:
    from onemore.modules.taste_profile import service as taste_service

    if db.get(TasteProfile, user_id) is not None:
        return
    result = CAST_TASTE.get(persona_id)
    if result is None:
        return
    import_id = ("imp_ov_" + user_id.replace("-", ""))[:36]
    now = datetime.now(UTC)
    session = db.get(TasteImportSession, import_id)
    if session is None:
        session = TasteImportSession(
            id=import_id,
            user_id=user_id,
            status=taste_service.READY,
            expires_at=now + timedelta(days=30),
        )
        db.add(session)
    session.status = taste_service.READY
    session.completed_at = now
    spec = CAST_BY_ID.get(persona_id)
    session.source_profile = {
        "nickname": spec.display_name if spec else "同学",
        "avatar_url": None,
        "uid": f"overlap-{user_id}",
    }
    session.result_snapshot = taste_service.normalize_taste_result(result) or result
    taste_service.upsert_taste_profile(db, session, result)


def attach_user_to_overlap(db: Session, user: User, *, persona_id: str = LIN) -> None:
    user.social_enabled = True
    user.course_matching_enabled = True
    user.account_status = "active"
    for code in PEER_OVERLAP_COURSE_CODES:
        ensure_enrollment(db, user.id, code)
    ensure_gym_slots(db, user.id, PEER_OVERLAP_GYM)
    copy_persona_taste(db, user.id, persona_id)


def attach_live_test_users(db: Session) -> list[str]:
    attached: list[str] = []
    for phone in LIVE_TEST_PHONES:
        user = db.scalar(select(User).where(User.phone == phone))
        if user is None:
            continue
        attach_user_to_overlap(db, user, persona_id=LIN)
        attached.append(user.id)
    if attached:
        db.commit()
        seed_live_partner_chats(db)
    return attached


def apply_peer_overlap_template(db: Session) -> dict[str, list[str]]:
    """Idempotent: refresh cast overlap + attach live test phones."""
    from onemore.db.seed import _seed_taste, _seed_users, seed_reference_data

    seed_reference_data(db)
    now = datetime.now(UTC)
    _seed_users(db, now)
    _seed_taste(db, now)
    seed_cast_gym_slots(db)
    live = attach_live_test_users(db)
    return {
        "cast_ids": [spec.id for spec in CAST_USERS],
        "live_ids": live,
        "courses": list(PEER_OVERLAP_COURSE_CODES),
        "gym": [PEER_OVERLAP_GYM.venue_type, PEER_OVERLAP_BASKETBALL.venue_type],
    }


_RELATION_CHAT_FALLBACK: dict[str, tuple[str, str, str]] = {
    "羽毛球": ("下场还去英东吗？", "去，我这周晚上都还行。", "那我先盯着订场。"),
    "运动搭子": ("下场还去英东吗？", "去，我这周晚上都还行。", "那我先盯着订场。"),
    "DDL冲刺": ("你到了吗？我在三楼。", "马上，电梯有点慢。", "我先占着靠窗的位置。"),
    "自习搭子": ("图书馆见，别占我插座。", "知道了，我带了排插。", "结束一起下楼。"),
    "讲座": ("门口见，别进错厅。", "好，我班车到了跟你说。", "人多的话我举个手。"),
    "比赛组队": ("材料今晚能出一版。", "好，我按这个改说明。", "有问题直接丢这里。"),
}

LIVE_CHAT_THREADS: tuple[dict, ...] = (
    {
        "partner_id": LIN,
        "title": "南校园羽毛球回访",
        "gathering_type": "羽毛球",
        "campus": "南校园",
        "location": "南校园英东体育中心",
        "days_ago": 12,
        "lines": (
            (LIN, "下次还是英东吧，我可以再订一场。"),
            ("live", "可以，周三晚上我有空。"),
            (LIN, "那我先占着，差拍你跟我说一声。"),
        ),
    },
    {
        "partner_id": CHEN,
        "title": "东校图书馆对进度",
        "gathering_type": "DDL冲刺",
        "campus": "东校园",
        "location": "东校园图书馆三楼",
        "days_ago": 8,
        "lines": (
            (CHEN, "三楼窗边那排我占了两个位。"),
            ("live", "我二十分钟到，你先开始。"),
            (CHEN, "好，我戴耳机赶海报，结束一起下楼。"),
        ),
    },
    {
        "partner_id": LIANG,
        "title": "逸夫讲座同行回访",
        "gathering_type": "讲座",
        "campus": "南校园",
        "location": "南校园逸夫文化艺术中心",
        "days_ago": 5,
        "lines": (
            (LIANG, "周五逸夫那场你还去吗？"),
            ("live", "去，听完门口见。"),
            (LIANG, "人多的话我在南门等你。"),
        ),
    },
    {
        "partner_id": HE,
        "title": "英东补一场",
        "gathering_type": "羽毛球",
        "campus": "南校园",
        "location": "南校园英东体育中心",
        "days_ago": 3,
        "lines": (
            (HE, "我从东校骑过去，别等我热身。"),
            ("live", "行，我先占场。"),
            (HE, "到了喊一声就行。"),
        ),
    },
)


def _pair_ids(user_a: str, user_b: str) -> tuple[str, str]:
    return (user_a, user_b) if user_a < user_b else (user_b, user_a)


def _channel_has_human_message(db: Session, channel_id: str) -> bool:
    return (
        db.scalar(
            select(Message.id).where(
                Message.channel_id == channel_id,
                Message.sender_type == "human",
            )
        )
        is not None
    )


def _add_chat_lines(
    db: Session,
    channel_id: str,
    lines: list[tuple[str, str]],
    *,
    start_at: datetime,
) -> None:
    members = list(
        db.scalars(
            select(ChannelParticipant).where(ChannelParticipant.channel_id == channel_id)
        )
    )
    start = ensure_utc(start_at)
    join_at = start - timedelta(minutes=20)
    for member in members:
        if ensure_utc(member.joined_at) > join_at:
            member.joined_at = join_at
    sent = start
    for sender_id, content in lines:
        db.add(
            Message(
                channel_id=channel_id,
                sender_id=sender_id,
                sender_type="human",
                content_type="text",
                content=content,
                sent_at=sent,
            )
        )
        sent += timedelta(minutes=7)


def _ensure_relation_channel(db: Session, relation: Relation) -> Channel:
    channel = db.scalar(select(Channel).where(Channel.relation_id == relation.id))
    if channel is None:
        channel = Channel(relation_id=relation.id, status=ChannelStatus.OPEN.value)
        db.add(channel)
        db.flush()
        db.add_all(
            [
                ChannelParticipant(channel_id=channel.id, user_id=relation.participant_a_id),
                ChannelParticipant(channel_id=channel.id, user_id=relation.participant_b_id),
            ]
        )
        return channel
    channel.status = ChannelStatus.OPEN.value
    channel.archived_at = None
    existing = set(
        db.scalars(
            select(ChannelParticipant.user_id).where(ChannelParticipant.channel_id == channel.id)
        )
    )
    for user_id in (relation.participant_a_id, relation.participant_b_id):
        if user_id not in existing:
            db.add(ChannelParticipant(channel_id=channel.id, user_id=user_id))
    return channel


def seed_relation_chat_previews(db: Session) -> int:
    """Fill empty 1:1 partner channels so the messages tab looks like chats."""
    from onemore.db.models import SharedExperience

    filled = 0
    channels = list(
        db.scalars(
            select(Channel).where(
                Channel.relation_id.is_not(None),
                Channel.status == ChannelStatus.OPEN.value,
            )
        )
    )
    for channel in channels:
        if channel.relation_id is None or _channel_has_human_message(db, channel.id):
            continue
        relation = db.get(Relation, channel.relation_id)
        if relation is None:
            continue
        experience = db.scalar(
            select(SharedExperience)
            .where(SharedExperience.relation_id == relation.id)
            .order_by(SharedExperience.occurred_at.desc())
        )
        kind = experience.gathering_type if experience is not None else ""
        first, second, third = _RELATION_CHAT_FALLBACK.get(
            kind, ("下次还去吗？", "去，我这周都还行。", "那到时候这里说一声。")
        )
        start_at = (experience.occurred_at if experience is not None else datetime.now(UTC)) + timedelta(
            minutes=20
        )
        _add_chat_lines(
            db,
            channel.id,
            [
                (relation.participant_a_id, first),
                (relation.participant_b_id, second),
                (relation.participant_a_id, third),
            ],
            start_at=start_at,
        )
        filled += 1
    if filled:
        db.commit()
    return filled


def _find_live_chat_gathering(db: Session, live_id: str, partner_id: str) -> Gathering | None:
    rows = db.scalars(
        select(Gathering).where(
            Gathering.status == GatheringStatus.COMPLETED.value,
            Gathering.owner_user_id.in_((live_id, partner_id)),
        )
    )
    wanted = {live_id, partner_id}
    for gathering in rows:
        meta = gathering.official_metadata if isinstance(gathering.official_metadata, dict) else {}
        if meta.get("seed") != "live_partner_chat":
            continue
        if {meta.get("live_user_id"), meta.get("partner_id")} == wanted:
            return gathering
    return None


def seed_live_partner_chats(db: Session) -> list[str]:
    """Give live test phones 1:1 chats with demo cast partners."""
    from onemore.modules.collab.service import record_experience

    opened: list[str] = []
    for phone in LIVE_TEST_PHONES:
        live = db.scalar(select(User).where(User.phone == phone))
        if live is None:
            continue
        live.social_enabled = True
        for spec in LIVE_CHAT_THREADS:
            partner_id = str(spec["partner_id"])
            if db.get(User, partner_id) is None:
                continue
            gathering = _find_live_chat_gathering(db, live.id, partner_id)
            if gathering is None:
                now = datetime.now(UTC)
                start_at = now - timedelta(days=int(spec["days_ago"]), hours=3)
                end_at = start_at + timedelta(hours=2)
                gathering = Gathering(
                    owner_user_id=partner_id,
                    gathering_type=str(spec["gathering_type"]),
                    mode="similar",
                    title=str(spec["title"]),
                    goal=str(spec["title"]),
                    status=GatheringStatus.COMPLETED.value,
                    min_size=2,
                    target_size=2,
                    required_trust_level="T0",
                    campus=str(spec["campus"]),
                    identity_disclosure="after_confirmed",
                    start_at=start_at,
                    end_at=end_at,
                    location=str(spec["location"]),
                    completed_at=end_at,
                    official_metadata={
                        "created_via": "self_initiation",
                        "seed": "live_partner_chat",
                        "live_user_id": live.id,
                        "partner_id": partner_id,
                    },
                )
                db.add(gathering)
                db.flush()
                for member_id, via in ((partner_id, "owner"), (live.id, "open")):
                    db.add(
                        GatheringMember(
                            gathering_id=gathering.id,
                            user_id=member_id,
                            confirmation_status=ConfirmationStatus.CONFIRMED.value,
                            joined_via=via,
                            confirmed_at=start_at - timedelta(hours=12),
                            completion_confirmed=True,
                        )
                    )
                db.flush()
                record_experience(db, gathering.id)
            relation = db.scalar(
                select(Relation).where(
                    Relation.participant_a_id == _pair_ids(live.id, partner_id)[0],
                    Relation.participant_b_id == _pair_ids(live.id, partner_id)[1],
                )
            )
            if relation is None:
                continue
            channel = _ensure_relation_channel(db, relation)
            if not _channel_has_human_message(db, channel.id):
                resolved = [
                    (live.id if sender == "live" else sender, text)
                    for sender, text in spec["lines"]
                ]
                hours_ago = {12: 26, 8: 10, 5: 4, 3: 1}.get(int(spec["days_ago"]), 6)
                stamp = datetime.now(UTC) - timedelta(hours=hours_ago)
                _add_chat_lines(db, channel.id, resolved, start_at=stamp)
            opened.append(channel.id)
    if opened:
        db.commit()
    return opened
