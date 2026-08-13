"""Shared course / gym overlap for Hermes peer matching demos.

Cast users keep their own majors, but many also take 机器学习 / 人工智能伦理 /
体育选修羽毛球, and several hold the same 南校园羽毛球 evening slot. Live test
phones (e.g. 15522668322) can be attached to the same template without
overwriting display name.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.db.demo_cast import (
    CAST_BY_ID,
    CAST_TASTE,
    CAST_USERS,
    COURSE_MEETINGS,
    LIN,
    LIVE_TEST_PHONES,
    PEER_OVERLAP_COURSE_CODES,
    PEER_OVERLAP_GYM,
    CastGymSlot,
)
from onemore.db.models import CampusAction, Course, Enrollment, TasteImportSession, TasteProfile, User

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
        "gym": [PEER_OVERLAP_GYM.venue_type],
    }
