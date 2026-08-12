from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Gathering,
    GatheringMember,
    GatheringStatus,
    TrustLevel,
    TrustProfile,
    User,
)
from onemore.modules.trust import service as trust_service


def _user(db: Session, suffix: str, *, level: str = TrustLevel.T1.value) -> User:
    user = User(
        id=f"u_trust_{suffix}",
        display_name="信任边界测试",
        verified_at=datetime.now(UTC),
        social_enabled=True,
    )
    db.add(user)
    db.flush()
    db.add(TrustProfile(user_id=user.id, level=level))
    db.flush()
    return user


def _completed(
    db: Session,
    user: User,
    *,
    count: int = 10,
    owned: int = 3,
    prefix: str,
) -> None:
    for index in range(count):
        is_owner = index < owned
        gathering = Gathering(
            id=f"g_{prefix}_{index}",
            owner_user_id=user.id if is_owner else "u_demo_2",
            gathering_type="study",
            title="有效成局",
            goal="完成测试",
            status=GatheringStatus.COMPLETED.value,
        )
        db.add(gathering)
        db.add(
            GatheringMember(
                gathering_id=gathering.id,
                user_id=user.id,
                joined_via="owner" if is_owner else "matching",
                completion_confirmed=True,
            )
        )
    db.flush()


def _events(db: Session, user: User, event_type: str, count: int, prefix: str) -> None:
    for index in range(count):
        trust_service.record_event(
            db,
            user.id,
            event_type,
            f"{prefix}-{event_type}-{index}",
        )


def test_t3_failure_rate_includes_no_shows_and_uses_strict_ten_percent_boundary():
    with SessionLocal() as db:
        below = _user(db, "below")
        _completed(db, below, prefix="below")
        _events(db, below, "recurred", 2, "below")
        _events(db, below, "on_time_confirm", 10, "below")
        _events(db, below, "no_show", 1, "below")
        below_profile = trust_service.recompute_level(db, below.id)
        assert below_profile.level == TrustLevel.T3.value
        assert below_profile.late_exit_rate == 1 / 11

        boundary = _user(db, "boundary")
        _completed(db, boundary, prefix="boundary")
        _events(db, boundary, "recurred", 2, "boundary")
        _events(db, boundary, "on_time_confirm", 9, "boundary")
        _events(db, boundary, "no_show", 1, "boundary")
        boundary_profile = trust_service.recompute_level(db, boundary.id)
        assert boundary_profile.level != TrustLevel.T3.value
        assert boundary_profile.late_exit_rate == 0.1


def test_t3_initiated_count_only_includes_completed_owned_attendance():
    with SessionLocal() as db:
        user = _user(db, "initiated")
        _completed(db, user, owned=0, prefix="initiated-valid")
        for index in range(3):
            gathering = Gathering(
                id=f"g_initiated_dissolved_{index}",
                owner_user_id=user.id,
                gathering_type="study",
                title="未完成发起",
                goal="不应计数",
                status=GatheringStatus.DISSOLVED.value,
            )
            db.add(gathering)
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user.id,
                    joined_via="owner",
                    completion_confirmed=False,
                )
            )
        _events(db, user, "recurred", 2, "initiated")
        _events(db, user, "on_time_confirm", 10, "initiated")
        profile = trust_service.recompute_level(db, user.id)
        assert profile.completed_gatherings == 10
        assert profile.initiated_gatherings == 0
        assert profile.level != TrustLevel.T3.value


def test_f16_downgrade_is_one_level_observed_and_not_reapplied():
    with SessionLocal() as db:
        user = _user(db, "observation", level=TrustLevel.T4.value)
        profile = db.get(TrustProfile, user.id)
        assert profile is not None
        profile.organizer_verified = True
        _events(db, user, "no_show", 2, "observation")
        downgraded = trust_service.recompute_level(db, user.id)
        assert downgraded.level == TrustLevel.T3.value
        assert downgraded.previous_level == TrustLevel.T4.value
        assert downgraded.observation_until is not None

        repeated = trust_service.recompute_level(db, user.id)
        assert repeated.level == TrustLevel.T3.value
        assert repeated.previous_level == TrustLevel.T4.value


def test_f16_late_exit_rate_is_strictly_over_twenty_five_percent():
    with SessionLocal() as db:
        boundary = _user(db, "exit_boundary", level=TrustLevel.T4.value)
        boundary_profile = db.get(TrustProfile, boundary.id)
        assert boundary_profile is not None
        boundary_profile.organizer_verified = True
        _events(db, boundary, "on_time_confirm", 3, "exit-boundary")
        _events(db, boundary, "late_exit", 1, "exit-boundary")
        assert trust_service.recompute_level(db, boundary.id).level == TrustLevel.T4.value

        over = _user(db, "exit_over", level=TrustLevel.T4.value)
        over_profile = db.get(TrustProfile, over.id)
        assert over_profile is not None
        over_profile.organizer_verified = True
        _events(db, over, "on_time_confirm", 2, "exit-over")
        _events(db, over, "late_exit", 1, "exit-over")
        downgraded = trust_service.recompute_level(db, over.id)
        assert downgraded.level == TrustLevel.T3.value
        assert downgraded.observation_until is not None
