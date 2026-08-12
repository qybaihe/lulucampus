"""Tick the demo cast through the same services a real student would hit.

Cadence is intentionally sparse: class hours block social posts, quiet hours
sleep, each person has a cooldown, and seeded gap cards stay open for humans.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.errors import AppError
from onemore.core.time import ensure_utc
from onemore.db.models import (
    CastDriverEvent,
    Channel,
    ChannelParticipant,
    ChannelStatus,
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    GatheringTransition,
    IntentCard,
    IntentStatus,
    Message,
    User,
)
from onemore.modules.cast_driver.catalog import (
    CAST_USER_IDS,
    PERSONAS,
    RESERVED_GAP_TITLES,
    ClassBlock,
    DriverPersona,
    IntentScript,
)
from onemore.modules.collab import service as collab_service
from onemore.modules.gathering import service as gathering_service
from onemore.modules.intent import service as intent_service
from onemore.modules.intent.schemas import IntentCardPatch, IntentCompileRequest
from onemore.modules.matching.service import run_matching

SHANGHAI = ZoneInfo("Asia/Shanghai")
QUIET_HOURS = frozenset({23, 0, 1, 2, 3, 4, 5, 6, 7})
REACTIVE_KINDS = frozenset({"confirm", "complete", "attend_class"})
PROACTIVE_KINDS = frozenset({"publish", "join", "chat"})
JOINABLE_STATUSES = {GatheringStatus.POOLING.value}
CHATTABLE_STATUSES = {
    GatheringStatus.CONFIRMED.value,
    GatheringStatus.PREVIEWED.value,
    GatheringStatus.EXECUTED.value,
    GatheringStatus.ACTIVE.value,
}
COMPLETABLE_STATUSES = {
    GatheringStatus.EXECUTED.value,
    GatheringStatus.ACTIVE.value,
}


def _local(now: datetime) -> datetime:
    return ensure_utc(now).astimezone(SHANGHAI)


def _day_start(now: datetime) -> datetime:
    local = _local(now)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def _is_quiet(now: datetime) -> bool:
    return _local(now).hour in QUIET_HOURS


def _class_block(persona: DriverPersona, now: datetime) -> ClassBlock | None:
    local = _local(now)
    for block in persona.class_blocks:
        if local.weekday() != block.weekday:
            continue
        start = local.replace(hour=block.start_hour, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=block.duration_hours)
        if start <= local < end:
            return block
    return None


def _next_slot(now: datetime, weekday: int, hour: int, duration_hours: int) -> tuple[datetime, datetime]:
    local = _local(now)
    days = (weekday - local.weekday()) % 7
    start = local.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days)
    if start <= local + timedelta(minutes=30):
        start += timedelta(days=7)
    end = start + timedelta(hours=duration_hours)
    return start.astimezone(UTC), end.astimezone(UTC)


def _record(
    db: Session,
    user_id: str,
    kind: str,
    *,
    now: datetime,
    subject_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> CastDriverEvent:
    event = CastDriverEvent(
        user_id=user_id,
        kind=kind,
        subject_id=subject_id,
        detail=detail or {},
        occurred_at=ensure_utc(now),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _events_since(db: Session, user_id: str, since: datetime, kind: str | None = None) -> list[CastDriverEvent]:
    query = select(CastDriverEvent).where(
        CastDriverEvent.user_id == user_id,
        CastDriverEvent.occurred_at >= ensure_utc(since),
    )
    if kind is not None:
        query = query.where(CastDriverEvent.kind == kind)
    return list(db.scalars(query.order_by(CastDriverEvent.occurred_at.desc())))


def _last_proactive(db: Session, user_id: str) -> CastDriverEvent | None:
    return db.scalar(
        select(CastDriverEvent)
        .where(
            CastDriverEvent.user_id == user_id,
            CastDriverEvent.kind.in_(tuple(PROACTIVE_KINDS)),
        )
        .order_by(CastDriverEvent.occurred_at.desc())
        .limit(1)
    )


def _already_did(db: Session, user_id: str, kind: str, subject_id: str, since: datetime) -> bool:
    return (
        db.scalar(
            select(func.count()).select_from(CastDriverEvent).where(
                CastDriverEvent.user_id == user_id,
                CastDriverEvent.kind == kind,
                CastDriverEvent.subject_id == subject_id,
                CastDriverEvent.occurred_at >= ensure_utc(since),
            )
        )
        or 0
    ) > 0


def _is_reserved(gathering: Gathering) -> bool:
    meta = gathering.official_metadata or {}
    return bool(meta.get("gap_for_real_user")) or gathering.title in RESERVED_GAP_TITLES


def _type_fits(persona: DriverPersona, gathering: Gathering) -> bool:
    haystack = f"{gathering.gathering_type} {gathering.title} {gathering.goal}"
    return any(token in haystack for token in persona.join_types)


def _campus_ok(persona: DriverPersona, campus: str | None) -> bool:
    if not campus:
        return True
    return campus in persona.travel_campuses


def _pending_confirms(db: Session, user_id: str) -> list[tuple[Gathering, GatheringMember]]:
    rows = list(
        db.execute(
            select(Gathering, GatheringMember)
            .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
            .where(
                GatheringMember.user_id == user_id,
                GatheringMember.left_at.is_(None),
                GatheringMember.confirmation_status == ConfirmationStatus.PENDING.value,
                Gathering.status == GatheringStatus.TENTATIVE.value,
            )
        )
    )
    return [(gathering, member) for gathering, member in rows]


def _pending_completes(db: Session, user_id: str, now: datetime) -> list[Gathering]:
    gatherings = list(
        db.scalars(
            select(Gathering)
            .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
            .where(
                GatheringMember.user_id == user_id,
                GatheringMember.left_at.is_(None),
                GatheringMember.completion_confirmed.is_(False),
                Gathering.status.in_(tuple(COMPLETABLE_STATUSES)),
                Gathering.end_at.is_not(None),
                Gathering.end_at <= ensure_utc(now),
            )
        )
    )
    return gatherings


def _tentative_at(db: Session, gathering_id: str) -> datetime | None:
    occurred = db.scalar(
        select(GatheringTransition.occurred_at)
        .where(
            GatheringTransition.gathering_id == gathering_id,
            GatheringTransition.to_status == GatheringStatus.TENTATIVE.value,
        )
        .order_by(GatheringTransition.occurred_at.desc())
        .limit(1)
    )
    return ensure_utc(occurred) if occurred is not None else None


def _has_open_intent(db: Session, user_id: str) -> bool:
    return (
        db.scalar(
            select(func.count()).select_from(IntentCard).where(
                IntentCard.user_id == user_id,
                IntentCard.status == IntentStatus.POOLING.value,
            )
        )
        or 0
    ) > 0


def _pick_script(persona: DriverPersona, now: datetime, rng: random.Random) -> IntentScript | None:
    local = _local(now)
    eligible = [
        script
        for script in persona.scripts
        if local.weekday() in script.weekdays and local.hour in script.hours
    ]
    if not eligible:
        return None
    return rng.choice(eligible)


def _attend(db: Session, user: User, block: ClassBlock, now: datetime) -> dict[str, Any]:
    subject = f"{block.course_code}:{_local(now).date().isoformat()}"
    if _already_did(db, user.id, "attend_class", subject, _day_start(now)):
        return {"kind": "attend_class", "skipped": True, "reason": "already_in_class"}
    _record(
        db,
        user.id,
        "attend_class",
        now=now,
        subject_id=subject,
        detail={
            "course_code": block.course_code,
            "course_name": block.course_name,
            "location": block.location,
        },
    )
    return {
        "kind": "attend_class",
        "user_id": user.id,
        "course": block.course_name,
        "location": block.location,
    }


def _confirm_due(db: Session, user: User, persona: DriverPersona, now: datetime) -> dict[str, Any] | None:
    for gathering, _member in _pending_confirms(db, user.id):
        matched_at = _tentative_at(db, gathering.id) or ensure_utc(gathering.updated_at)
        waited = ensure_utc(now) - matched_at
        deadline = (
            ensure_utc(gathering.confirmation_deadline)
            if gathering.confirmation_deadline is not None
            else None
        )
        rush = deadline is not None and deadline - ensure_utc(now) <= timedelta(minutes=20)
        if waited < timedelta(minutes=persona.confirm_delay_minutes) and not rush:
            continue
        gathering_service.confirm(db, gathering.id, user.id, True)
        _record(db, user.id, "confirm", now=now, subject_id=gathering.id, detail={"title": gathering.title})
        return {"kind": "confirm", "user_id": user.id, "gathering_id": gathering.id, "title": gathering.title}
    return None


def _complete_due(db: Session, user: User, now: datetime) -> dict[str, Any] | None:
    for gathering in _pending_completes(db, user.id, now):
        gathering_service.complete(db, gathering.id, user.id, True)
        _record(db, user.id, "complete", now=now, subject_id=gathering.id, detail={"title": gathering.title})
        return {"kind": "complete", "user_id": user.id, "gathering_id": gathering.id, "title": gathering.title}
    return None


def _publish(
    db: Session,
    user: User,
    persona: DriverPersona,
    now: datetime,
    rng: random.Random,
) -> dict[str, Any] | None:
    if not persona.hosts or not persona.scripts:
        return None
    if _has_open_intent(db, user.id):
        return None
    if _events_since(db, user.id, _day_start(now), "publish"):
        return None
    script = _pick_script(persona, now, rng)
    if script is None:
        return None
    weekday = script.start_weekday if script.start_weekday is not None else _local(now).weekday()
    start, end = _next_slot(now, weekday, script.start_hour, script.duration_hours)
    answers: dict[str, str] = {
        "availability": f"{start.isoformat()}|{end.isoformat()}",
    }
    if script.roles:
        answers["required_roles"] = script.roles
    card, questions = intent_service.compile_intent(
        db,
        user,
        IntentCompileRequest(text=script.text, mood_note=script.mood_note, answers=answers),
    )
    if questions and card.status != IntentStatus.DRAFT.value:
        card, questions = intent_service.compile_intent(
            db,
            user,
            IntentCompileRequest(
                text=script.text,
                mood_note=script.mood_note,
                clarification_round=1,
                answers=answers,
            ),
        )
    if card.status != IntentStatus.DRAFT.value:
        return None
    intent_service.edit_card(db, card.id, user.id, IntentCardPatch(campus=script.campus))
    _card, gathering = intent_service.publish(db, card.id, user)
    meta = dict(gathering.official_metadata or {})
    meta["created_via"] = "cast_driver"
    meta["script"] = script.key
    gathering.official_metadata = meta
    db.commit()
    _record(
        db,
        user.id,
        "publish",
        now=now,
        subject_id=gathering.id,
        detail={"script": script.key, "intent_id": card.id, "title": gathering.title},
    )
    return {
        "kind": "publish",
        "user_id": user.id,
        "gathering_id": gathering.id,
        "intent_id": card.id,
        "title": gathering.title,
    }


def _join(
    db: Session,
    user: User,
    persona: DriverPersona,
    now: datetime,
    rng: random.Random,
) -> dict[str, Any] | None:
    if _events_since(db, user.id, _day_start(now), "join"):
        return None
    if user.minimum_group_size > 4:
        return None
    open_items = gathering_service.list_open(db, viewer_id=user.id)
    rng.shuffle(open_items)
    for gathering in open_items:
        if gathering.owner_user_id == user.id:
            continue
        if _is_reserved(gathering):
            continue
        if not _type_fits(persona, gathering):
            continue
        if not _campus_ok(persona, gathering.campus):
            continue
        if gathering.min_size < user.minimum_group_size:
            continue
        members = gathering_service.active_members(db, gathering.id)
        if any(member.user_id == user.id for member in members):
            continue
        remaining = gathering.target_size - len(members)
        if remaining <= 0:
            continue
        # Keep a human seat on 4+ person boards; fill 3-person boards so they can form.
        if remaining == 1 and gathering.target_size >= 4:
            continue
        gathering_service.join(db, gathering.id, user, None, "open")
        _record(
            db,
            user.id,
            "join",
            now=now,
            subject_id=gathering.id,
            detail={"title": gathering.title},
        )
        return {
            "kind": "join",
            "user_id": user.id,
            "gathering_id": gathering.id,
            "title": gathering.title,
        }
    return None


def _chat(
    db: Session,
    user: User,
    persona: DriverPersona,
    now: datetime,
    rng: random.Random,
) -> dict[str, Any] | None:
    if _events_since(db, user.id, _day_start(now), "chat"):
        return None
    if rng.random() > persona.chat_probability:
        return None
    rows = list(
        db.execute(
            select(Gathering, Channel)
            .join(Channel, Channel.gathering_id == Gathering.id)
            .join(ChannelParticipant, ChannelParticipant.channel_id == Channel.id)
            .where(
                ChannelParticipant.user_id == user.id,
                Channel.status == ChannelStatus.OPEN.value,
                Gathering.status.in_(tuple(CHATTABLE_STATUSES)),
            )
        )
    )
    for gathering, channel in rows:
        opened = ensure_utc(channel.opened_at)
        if ensure_utc(now) - opened < timedelta(minutes=12):
            continue
        if _already_did(db, user.id, "chat", gathering.id, _day_start(now)):
            continue
        last = db.scalar(
            select(Message)
            .where(Message.channel_id == channel.id, Message.sender_type == "human")
            .order_by(Message.sent_at.desc())
            .limit(1)
        )
        if last is not None and last.sender_id == user.id:
            continue
        line = rng.choice(persona.chat_lines)
        collab_service.send_message(db, channel.id, user.id, line)
        _record(
            db,
            user.id,
            "chat",
            now=now,
            subject_id=gathering.id,
            detail={"channel_id": channel.id, "preview": line},
        )
        return {
            "kind": "chat",
            "user_id": user.id,
            "gathering_id": gathering.id,
            "channel_id": channel.id,
        }
    return None


def _cooldown_ok(db: Session, persona: DriverPersona, now: datetime) -> bool:
    last = _last_proactive(db, persona.user_id)
    if last is None:
        return True
    return ensure_utc(now) - ensure_utc(last.occurred_at) >= timedelta(hours=persona.cooldown_hours)


def _act_proactive(
    db: Session,
    user: User,
    persona: DriverPersona,
    now: datetime,
    rng: random.Random,
    *,
    allow_publish: bool,
    allow_join: bool,
) -> dict[str, Any] | None:
    if not _cooldown_ok(db, persona, now):
        return None
    # Hosts prefer publishing; quiet members prefer joining what already exists.
    order = ("publish", "join", "chat") if persona.hosts else ("join", "chat", "publish")
    for kind in order:
        if kind == "publish" and allow_publish:
            result = _publish(db, user, persona, now, rng)
            if result:
                return result
        elif kind == "join" and allow_join:
            result = _join(db, user, persona, now, rng)
            if result:
                return result
        elif kind == "chat":
            result = _chat(db, user, persona, now, rng)
            if result:
                return result
    return None


def tick(
    db: Session,
    *,
    now: datetime | None = None,
    rng: random.Random | None = None,
    enabled: bool | None = None,
    force: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    if enabled is None:
        enabled = settings.cast_driver_enabled
    if not enabled:
        return {"skipped": True, "reason": "disabled", "actions": []}
    if settings.is_production:
        return {"skipped": True, "reason": "production", "actions": []}

    now = ensure_utc(now or datetime.now(UTC))
    rng = rng or random.Random(f"{_local(now).strftime('%Y-%m-%dT%H')}{now.minute // 15}")
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    quiet = _is_quiet(now)
    publishes = 0
    joins = 0

    user_ids = list(CAST_USER_IDS)
    rng.shuffle(user_ids)

    for user_id in user_ids:
        user = db.get(User, user_id)
        persona = PERSONAS.get(user_id)
        if user is None or persona is None or not user.social_enabled:
            continue
        try:
            completed = _complete_due(db, user, now)
            if completed:
                actions.append(completed)
                continue
            confirmed = _confirm_due(db, user, persona, now)
            if confirmed:
                actions.append(confirmed)
                continue
            block = _class_block(persona, now)
            if block is not None:
                actions.append(_attend(db, user, block, now))
                continue
            if quiet and not force:
                skipped.append({"user_id": user_id, "reason": "quiet_hours"})
                continue
            if not force and rng.random() > persona.act_probability:
                skipped.append({"user_id": user_id, "reason": "not_in_the_mood"})
                continue
            result = _act_proactive(
                db,
                user,
                persona,
                now,
                rng,
                allow_publish=publishes < 1,
                allow_join=joins < 1,
            )
            if result is None:
                skipped.append({"user_id": user_id, "reason": "no_eligible_action"})
                continue
            actions.append(result)
            if result["kind"] == "publish":
                publishes += 1
            elif result["kind"] == "join":
                joins += 1
        except AppError as exc:
            skipped.append({"user_id": user_id, "reason": exc.code})

    matched = None
    if any(item["kind"] in {"publish", "join"} for item in actions):
        matched = run_matching(db)

    return {
        "skipped": False,
        "now": now.isoformat(),
        "quiet": quiet,
        "force": force,
        "actions": actions,
        "deferred": skipped,
        "matching": matched,
    }


def snapshot(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    now = ensure_utc(now or datetime.now(UTC))
    people = []
    for user_id in CAST_USER_IDS:
        user = db.get(User, user_id)
        persona = PERSONAS[user_id]
        block = _class_block(persona, now) if user is not None else None
        last = db.scalar(
            select(CastDriverEvent)
            .where(CastDriverEvent.user_id == user_id)
            .order_by(CastDriverEvent.occurred_at.desc())
            .limit(1)
        )
        people.append(
            {
                "user_id": user_id,
                "display_name": user.display_name if user is not None else None,
                "present": user is not None,
                "in_class": None
                if block is None
                else {
                    "course": block.course_name,
                    "location": block.location,
                },
                "pending_confirms": len(_pending_confirms(db, user_id)) if user else 0,
                "last_action": None
                if last is None
                else {
                    "kind": last.kind,
                    "at": last.occurred_at.isoformat(),
                    "subject_id": last.subject_id,
                },
            }
        )
    return {
        "enabled": get_settings().cast_driver_enabled,
        "now": now.isoformat(),
        "quiet": _is_quiet(now),
        "people": people,
    }
