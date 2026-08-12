from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Gathering,
    GatheringMember,
    GatheringStatus,
    Notification,
    TrustEvent,
    User,
)


def _completed_pair() -> str:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习",
            mode="similar",
            title="下周继续自习",
            goal="一起完成复局",
            status=GatheringStatus.COMPLETED.value,
            min_size=2,
            target_size=2,
            required_trust_level="T0",
            identity_disclosure="after_confirmed",
            start_at=now - timedelta(days=1, hours=2),
            end_at=now - timedelta(days=1),
            completed_at=now - timedelta(hours=20),
        )
        db.add(gathering)
        db.flush()
        db.add_all(
            [
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_1"),
                GatheringMember(gathering_id=gathering.id, user_id="u_demo_2"),
            ]
        )
        for user_id in ("u_demo_1", "u_demo_2"):
            user = db.get(User, user_id)
            assert user is not None
            user.minimum_group_size = 2
        db.commit()
        return gathering.id


def test_quiet_end_is_private_idempotent_and_sends_no_notification(client):
    gathering_id = _completed_pair()
    with SessionLocal() as db:
        before = db.scalar(select(func.count(Notification.id)))

    ended = client.post(
        f"/gatherings/{gathering_id}/recur/finish",
        headers={"X-User-ID": "u_demo_1"},
    )
    assert ended.status_code == 200, ended.text
    assert ended.json()["data"] == {
        "gathering_id": gathering_id,
        "decision": "ended",
        "notified": False,
    }
    repeated = client.post(
        f"/gatherings/{gathering_id}/recur/finish",
        headers={"X-User-ID": "u_demo_1"},
    )
    assert repeated.status_code == 200

    mine = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}
    ).json()["data"]
    peer = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_2"}
    ).json()["data"]
    assert mine["my_recurrence_decision"] == {
        "decision": "ended",
        "kept_user_ids": [],
        "clone_gathering_id": None,
    }
    assert peer["my_recurrence_decision"] is None
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Notification.id))) == before


def test_recurrence_signal_is_recorded_only_after_reunion_completes(client):
    gathering_id = _completed_pair()
    created = client.post(
        f"/gatherings/{gathering_id}/recur",
        headers={"X-User-ID": "u_demo_1"},
        json={"keep_user_ids": None},
    )
    assert created.status_code == 201, created.text
    clone = created.json()["data"]
    assert clone["status"] == GatheringStatus.TENTATIVE.value
    clone_id = clone["id"]

    with SessionLocal() as db:
        assert db.scalar(
            select(func.count(TrustEvent.id)).where(
                TrustEvent.reference_id == clone_id,
                TrustEvent.event_type == "recurred",
            )
        ) == 0

    first = client.post(
        f"/gatherings/{clone_id}/confirm",
        headers={"X-User-ID": "u_demo_1"},
        json={"confirmed": True},
    )
    assert first.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count(TrustEvent.id)).where(
                TrustEvent.reference_id == clone_id,
                TrustEvent.event_type == "recurred",
            )
        ) == 0

    second = client.post(
        f"/gatherings/{clone_id}/confirm",
        headers={"X-User-ID": "u_demo_2"},
        json={"confirmed": True},
    )
    assert second.status_code == 200
    assert second.json()["data"]["status"] == GatheringStatus.CONFIRMED.value
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count(TrustEvent.id)).where(
                TrustEvent.reference_id == clone_id,
                TrustEvent.event_type == "recurred",
            )
        ) == 0
        clone_row = db.get(Gathering, clone_id)
        assert clone_row is not None
        clone_row.status = GatheringStatus.EXECUTED.value
        clone_row.start_at = datetime.now(UTC) - timedelta(hours=2)
        clone_row.end_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    first_completion = client.post(
        f"/gatherings/{clone_id}/complete",
        headers={"X-User-ID": "u_demo_1"},
        json={"completed": True},
    )
    assert first_completion.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count(TrustEvent.id)).where(
                TrustEvent.reference_id == clone_id,
                TrustEvent.event_type == "recurred",
            )
        ) == 0

    last_completion = client.post(
        f"/gatherings/{clone_id}/complete",
        headers={"X-User-ID": "u_demo_2"},
        json={"completed": True},
    )
    assert last_completion.status_code == 200
    assert last_completion.json()["data"]["status"] == GatheringStatus.COMPLETED.value
    with SessionLocal() as db:
        events = list(
            db.scalars(
                select(TrustEvent).where(
                    TrustEvent.reference_id == clone_id,
                    TrustEvent.event_type == "recurred",
                )
            )
        )
        assert {event.user_id for event in events} == {"u_demo_1", "u_demo_2"}
        assert len(events) == 2
        original = db.get(Gathering, gathering_id)
        assert original is not None
        assert original.status == GatheringStatus.COMPLETED.value
