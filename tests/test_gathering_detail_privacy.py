from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import (
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    GatheringTransition,
    TrustEvent,
)


def _gathering(status: str) -> str:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        item = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习",
            mode="similar",
            title="仅成员可见的具体安排",
            goal="在宿舍楼内完成作业",
            status=status,
            min_size=2,
            target_size=2,
            required_trust_level="T1",
            campus="珠海校区",
            start_at=now + timedelta(hours=2),
            end_at=now + timedelta(hours=4),
            location="具体宿舍楼 3 栋 401",
            expires_at=now + timedelta(hours=1),
        )
        db.add(item)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2"):
            db.add(
                GatheringMember(
                    gathering_id=item.id,
                    user_id=user_id,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                )
            )
        db.commit()
        return item.id


def test_non_member_cannot_read_exact_details_after_identity_reveal(client):
    gathering_id = _gathering(GatheringStatus.CONFIRMED.value)

    denied = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_4"}
    )
    assert denied.status_code == 404
    assert "具体宿舍楼" not in denied.text

    member = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}
    )
    assert member.status_code == 200
    assert member.json()["data"]["location"] == "具体宿舍楼 3 栋 401"


def test_former_share_id_does_not_bypass_post_match_access_control(client):
    gathering_id = _gathering(GatheringStatus.POOLING.value)
    shared = client.post(
        f"/gatherings/{gathering_id}/share",
        headers={"X-User-ID": "u_demo_1", "Idempotency-Key": "privacy-share-1"},
        json={},
    )
    assert shared.status_code == 201
    assert shared.json()["data"]["gathering_id"] == gathering_id
    public_before_match = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_4"}
    )
    assert public_before_match.status_code == 200

    with SessionLocal() as db:
        item = db.get(Gathering, gathering_id)
        assert item is not None
        item.status = GatheringStatus.CONFIRMED.value
        db.commit()

    denied = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_4"}
    )
    assert denied.status_code == 404
    assert "具体宿舍楼" not in denied.text


def test_departed_member_has_durable_limited_safety_context_after_relaunch(client):
    gathering_id = _gathering(GatheringStatus.CONFIRMED.value)
    with SessionLocal() as db:
        db.add(
            GatheringTransition(
                gathering_id=gathering_id,
                from_status=GatheringStatus.TENTATIVE.value,
                to_status=GatheringStatus.CONFIRMED.value,
                event="all_confirmed",
                actor_user_id="u_demo_2",
            )
        )
        db.commit()

    left = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_1"},
        json={},
    )
    assert left.status_code == 200, left.text
    assert client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}
    ).status_code == 404

    history = client.get(
        "/gatherings/history/safety", headers={"X-User-ID": "u_demo_1"}
    )
    assert history.status_code == 200, history.text
    context = next(
        item
        for item in history.json()["data"]
        if item["gathering_id"] == gathering_id
    )
    assert context["title"] == "仅成员可见的具体安排"
    assert [item["user_id"] for item in context["reportable_participants"]] == [
        "u_demo_2"
    ]
    assert {"location", "start_at", "end_at", "goal", "member_count"}.isdisjoint(
        context
    )
    assert "具体宿舍楼 3 栋 401" not in history.text
    outsider = client.get(
        "/gatherings/history/safety", headers={"X-User-ID": "u_demo_4"}
    ).json()["data"]
    assert gathering_id not in {item["gathering_id"] for item in outsider}

    reported = client.post(
        f"/gatherings/{gathering_id}/report",
        headers={"X-User-ID": "u_demo_1"},
        json={
            "reported_user_id": "u_demo_2",
            "reason": "退出后重新启动仍需提交的安全事实",
            "block": True,
        },
    )
    assert reported.status_code == 200, reported.text


def test_leave_capability_exposes_authoritative_trust_impact(client):
    gathering_id = _gathering(GatheringStatus.CONFIRMED.value)
    far = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}
    )
    assert far.status_code == 200
    # The helper starts at about the two-hour boundary, so move it well clear
    # of that boundary for deterministic assertions.
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.start_at = datetime.now(UTC) + timedelta(hours=4)
        gathering.end_at = gathering.start_at + timedelta(hours=2)
        db.commit()
    far_capability = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}
    ).json()["data"]["leave_capability"]
    assert far_capability["enabled"] is True
    assert far_capability["trust_impact"] == "none"
    assert "不影响信任等级" in far_capability["message"]

    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.start_at = datetime.now(UTC) + timedelta(minutes=30)
        gathering.end_at = gathering.start_at + timedelta(hours=2)
        db.commit()
    near_capability = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}
    ).json()["data"]["leave_capability"]
    assert near_capability["trust_impact"] == "late_exit"
    assert "影响信任进度" in near_capability["message"]
    assert near_capability["late_exit_cutoff"] is not None
    assert near_capability["server_now"] is not None

    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.start_at = datetime.now(UTC) - timedelta(minutes=1)
        gathering.end_at = datetime.now(UTC) + timedelta(hours=2)
        db.commit()
    started = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}
    ).json()["data"]["leave_capability"]
    assert started["enabled"] is True
    assert started["trust_impact"] == "no_show"
    assert started["disabled_reason"] is None
    left = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_1"},
        json={},
    )
    assert left.status_code == 200, left.text
    with SessionLocal() as db:
        member = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == "u_demo_1",
            )
        )
        assert member is not None
        assert member.left_at is not None
        assert db.scalar(
            select(TrustEvent.id).where(
                TrustEvent.user_id == "u_demo_1",
                TrustEvent.reference_id == gathering_id,
                TrustEvent.event_type == "no_show",
            )
        ) is not None
        assert db.scalar(
            select(TrustEvent.id).where(
                TrustEvent.user_id == "u_demo_1",
                TrustEvent.reference_id == gathering_id,
                TrustEvent.event_type == "late_exit",
            )
        ) is None


@pytest.mark.parametrize(
    "terminal_status",
    [
        GatheringStatus.COMPLETED.value,
        GatheringStatus.RECURRENCE_PENDING.value,
        GatheringStatus.ARCHIVED.value,
        GatheringStatus.DISSOLVED.value,
    ],
)
def test_terminal_gathering_rejects_leave_without_side_effects(
    client, terminal_status: str
):
    gathering_id = _gathering(terminal_status)
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.start_at = datetime.now(UTC) - timedelta(hours=3)
        gathering.end_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()

    capability = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}
    ).json()["data"]["leave_capability"]
    assert capability["enabled"] is False
    assert capability["trust_impact"] == "none"

    response = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_1"},
        json={},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "GATHERING_LEAVE_CLOSED"

    with SessionLocal() as db:
        member = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == "u_demo_1",
            )
        )
        assert member is not None
        assert member.left_at is None
        assert db.scalar(
            select(TrustEvent.id).where(
                TrustEvent.user_id == "u_demo_1",
                TrustEvent.reference_id == gathering_id,
                TrustEvent.event_type.in_(("no_show", "late_exit")),
            )
        ) is None


@pytest.mark.parametrize("reason", ["declined", "DECLINED", " declined "])
def test_public_leave_reason_cannot_bypass_started_no_show(client, reason: str):
    gathering_id = _gathering(GatheringStatus.CONFIRMED.value)
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.start_at = datetime.now(UTC) - timedelta(minutes=10)
        gathering.end_at = datetime.now(UTC) + timedelta(hours=1)
        db.commit()

    response = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_1"},
        json={"reason": reason},
    )
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        member = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == "u_demo_1",
            )
        )
        assert member is not None
        assert member.left_at is not None
        assert db.scalar(
            select(TrustEvent.id).where(
                TrustEvent.user_id == "u_demo_1",
                TrustEvent.reference_id == gathering_id,
                TrustEvent.event_type == "no_show",
            )
        ) is not None


def test_public_declined_reason_cannot_bypass_late_exit(client):
    gathering_id = _gathering(GatheringStatus.CONFIRMED.value)
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.start_at = datetime.now(UTC) + timedelta(minutes=30)
        gathering.end_at = gathering.start_at + timedelta(hours=1)
        db.commit()

    response = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_1"},
        json={"reason": "declined"},
    )
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        member = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == "u_demo_1",
            )
        )
        assert member is not None
        assert member.left_at is not None
        assert db.scalar(
            select(TrustEvent.id).where(
                TrustEvent.user_id == "u_demo_1",
                TrustEvent.reference_id == gathering_id,
                TrustEvent.event_type == "late_exit",
            )
        ) is not None
