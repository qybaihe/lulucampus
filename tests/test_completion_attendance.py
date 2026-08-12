from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Gathering,
    GatheringMember,
    GatheringStatus,
    OrganizerAttendance,
    Relation,
    SharedGoal,
    SharedGoalMemberProgress,
    TrustEvent,
    TrustProfile,
)
from onemore.modules.gathering.service import (
    adjudicate_overdue_completion_outcomes,
    start_due_gatherings,
)


def _executed_gathering(*, official: bool = False, overdue: bool = False) -> str:
    with SessionLocal() as db:
        end_at = datetime.now(UTC) - (
            timedelta(hours=25) if overdue else timedelta(minutes=1)
        )
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习搭子",
            mode="similar",
            title="完成结果测试",
            goal="只记录本人结果或主理人签到事实",
            status=GatheringStatus.EXECUTED.value,
            min_size=2,
            target_size=2,
            start_at=end_at - timedelta(hours=1),
            end_at=end_at,
            is_official=official,
        )
        db.add(gathering)
        db.flush()
        db.add_all(
            [
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_1"),
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_2"),
            ]
        )
        db.commit()
        return gathering.id


def test_member_can_self_declare_no_show_once_without_exposing_a_reporter(client):
    with SessionLocal() as db:
        baseline_completed = db.get(TrustProfile, "u_demo_1").completed_gatherings
    gathering_id = _executed_gathering()
    first = client.post(
        f"/gatherings/{gathering_id}/complete",
        headers={"X-User-ID": "u_demo_1"},
        json={"completed": False},
    )
    assert first.status_code == 200, first.text
    duplicate = client.post(
        f"/gatherings/{gathering_id}/complete",
        headers={"X-User-ID": "u_demo_1"},
        json={"completed": False},
    )
    assert duplicate.status_code == 200
    finished = client.post(
        f"/gatherings/{gathering_id}/complete",
        headers={"X-User-ID": "u_demo_2"},
        json={"completed": True},
    )
    assert finished.status_code == 200
    assert finished.json()["data"]["status"] == GatheringStatus.COMPLETED.value
    with SessionLocal() as db:
        no_shows = db.scalar(
            select(func.count(TrustEvent.id)).where(
                TrustEvent.user_id == "u_demo_1",
                TrustEvent.event_type == "no_show",
                TrustEvent.reference_id == gathering_id,
            )
        )
        assert no_shows == 1
        profile = db.get(TrustProfile, "u_demo_1")
        assert profile is not None
        assert profile.no_show_count_30d == 1
        assert profile.completed_gatherings == baseline_completed
        assert db.scalar(select(Relation.id).where(Relation.created_from_gathering_id == gathering_id)) is None


def test_nonofficial_timeout_is_neutral_not_an_automatic_no_show():
    gathering_id = _executed_gathering(overdue=True)
    with SessionLocal() as db:
        result = adjudicate_overdue_completion_outcomes(db)
        assert result == {
            "gatherings": 1,
            "no_shows": 0,
            "unresolved": 2,
            "completed": 1,
        }
        events = list(
            db.scalars(
                select(TrustEvent).where(TrustEvent.reference_id == gathering_id)
            )
        )
        assert {event.event_type for event in events} == {"completion_unresolved"}
        assert all(event.weight == 0 for event in events)


def test_official_timeout_uses_t4_check_in_as_attendance_evidence():
    gathering_id = _executed_gathering(official=True, overdue=True)
    with SessionLocal() as db:
        db.add(
            OrganizerAttendance(
                gathering_id=gathering_id,
                user_id="u_demo_1",
            )
        )
        db.commit()
        result = adjudicate_overdue_completion_outcomes(db)
        assert result["no_shows"] == 1
        assert result["completed"] == 1
        outcomes = {
            (event.user_id, event.event_type)
            for event in db.scalars(
                select(TrustEvent).where(TrustEvent.reference_id == gathering_id)
            )
        }
        assert outcomes == {
            ("u_demo_1", "completion_confirmed"),
            ("u_demo_2", "no_show"),
        }


def test_confirmed_gathering_without_campus_action_becomes_active_at_start():
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="羽毛球",
            mode="similar",
            title="无需校园写操作",
            goal="按时开始普通局",
            status=GatheringStatus.CONFIRMED.value,
            min_size=2,
            target_size=2,
            start_at=now - timedelta(minutes=1),
            end_at=now + timedelta(hours=1),
        )
        db.add(gathering)
        db.flush()
        db.add_all(
            [
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_1"),
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_2"),
            ]
        )
        db.commit()
        gathering_id = gathering.id
        assert start_due_gatherings(db) == 1
        db.refresh(gathering)
        assert gathering.status == GatheringStatus.ACTIVE.value
        assert gathering.id == gathering_id


def test_completion_before_server_end_boundary_is_rejected_without_trust_event(client):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习",
            mode="similar",
            title="尚未结束",
            goal="不能提前沉淀",
            status=GatheringStatus.EXECUTED.value,
            min_size=2,
            target_size=2,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=1, hours=2),
        )
        db.add(gathering)
        db.flush()
        db.add_all(
            [
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_1"),
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_2"),
            ]
        )
        db.commit()
        gathering_id = gathering.id

    rejected = client.post(
        f"/gatherings/{gathering_id}/complete",
        headers={"X-User-ID": "u_demo_1"},
        json={"completed": True},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "GATHERING_NOT_ENDED"
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count(TrustEvent.id)).where(
                TrustEvent.reference_id == gathering_id,
                TrustEvent.event_type == "completion_confirmed",
            )
        ) == 0


def test_official_check_in_then_completion_counts_one_shared_goal_fact(client):
    """One gathering must never advance a goal twice via check-in + completion."""

    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习",
            mode="similar",
            title="共同目标去重",
            goal="同一局只计一次",
            status=GatheringStatus.EXECUTED.value,
            min_size=2,
            target_size=2,
            start_at=now - timedelta(hours=2),
            end_at=now - timedelta(minutes=1),
            is_official=True,
        )
        db.add(gathering)
        db.flush()
        db.add_all(
            [
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_1"),
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_2"),
            ]
        )
        relation = db.scalar(
            select(Relation).where(
                Relation.participant_a_id == "u_demo_1",
                Relation.participant_b_id == "u_demo_2",
            )
        )
        assert relation is not None
        relation.status = "active"
        goal = SharedGoal(
            relation_id=relation.id,
            definition="一起完成五次自习",
            period_start=now.date() - timedelta(days=1),
            period_end=now.date() + timedelta(days=30),
            target_value=5,
            unit="次",
            milestones=[],
        )
        db.add(goal)
        db.flush()
        db.add_all(
            [
                SharedGoalMemberProgress(goal_id=goal.id, user_id="u_demo_1"),
                SharedGoalMemberProgress(goal_id=goal.id, user_id="u_demo_2"),
            ]
        )
        db.commit()
        gathering_id = gathering.id
        goal_id = goal.id

    verified = client.post(
        "/internal/trust/u_demo_1/organizer-verification",
        headers={"X-Admin-Token": "test-admin"},
        json={"verified": True},
    )
    assert verified.status_code == 200, verified.text
    checked_in = client.post(
        f"/organizer/gatherings/{gathering_id}/attendance/u_demo_2",
        headers={"X-User-ID": "u_demo_1"},
    )
    assert checked_in.status_code == 200, checked_in.text
    completed = client.post(
        f"/gatherings/{gathering_id}/complete",
        headers={"X-User-ID": "u_demo_2"},
        json={"completed": True},
    )
    assert completed.status_code == 200, completed.text

    with SessionLocal() as db:
        progress = db.scalar(
            select(SharedGoalMemberProgress).where(
                SharedGoalMemberProgress.goal_id == goal_id,
                SharedGoalMemberProgress.user_id == "u_demo_2",
            )
        )
        assert progress is not None
        assert progress.current_value == 1
        assert progress.source_ids == [f"gathering:{gathering_id}"]
