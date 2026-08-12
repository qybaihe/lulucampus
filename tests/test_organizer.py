from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from onemore.core.database import SessionLocal
from onemore.db.models import Gathering, OrganizerAttendance, TrustEvent


def test_t4_organizer_supply_dashboard_and_template(client, admin_headers, auth_headers):
    start_at = datetime.now(UTC) + timedelta(days=20)
    end_at = start_at + timedelta(hours=2)
    verified = client.post(
        "/internal/trust/u_demo_1/organizer-verification",
        headers=admin_headers,
        json={"verified": True},
    )
    assert verified.status_code == 200
    assert verified.json()["data"]["level"] == "T4"

    created = client.post(
        "/organizer/gatherings",
        headers=auth_headers,
        json={
            "title": "校园创新工作坊",
            "goal": "完成一次跨专业原型共创",
            "gathering_type": "workshop",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "location": "珠海校区创新空间",
            "campus": "珠海校区",
            "min_size": 3,
            "target_size": 20,
            "quota_batches": [
                {"label": "公开名额", "slots": 15},
                {"label": "候补名额", "slots": 5},
            ],
        },
    )
    assert created.status_code == 201, created.text
    gathering_id = created.json()["data"]["id"]
    dashboard = client.get(
        f"/organizer/gatherings/{gathering_id}/dashboard", headers=auth_headers
    ).json()["data"]
    assert dashboard["registered_count"] == 1
    assert dashboard["participants"] is None
    assert dashboard["identity_visibility"] == "after_confirmed"

    for user_id in ("u_demo_2", "u_demo_3"):
        joined = client.post(
            f"/gatherings/{gathering_id}/join",
            headers={"X-User-ID": user_id},
            json={},
        )
        assert joined.status_code == 200
    still_pooling = client.get(
        f"/organizer/gatherings/{gathering_id}/dashboard", headers=auth_headers
    ).json()["data"]
    assert still_pooling["status"] == "Pooling"
    assert still_pooling["registered_count"] == 3
    closed = client.post(
        f"/organizer/gatherings/{gathering_id}/close-registration",
        headers=auth_headers,
    )
    assert closed.json()["data"]["status"] == "Tentative"
    for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
        confirmed = client.post(
            f"/gatherings/{gathering_id}/confirm",
            headers={"X-User-ID": user_id},
            json={"confirmed": True},
        )
        assert confirmed.status_code == 200
    finalized = client.post(f"/organizer/gatherings/{gathering_id}/finalize", headers=auth_headers)
    assert finalized.json()["data"]["status"] == "Executed"
    visible_dashboard = client.get(
        f"/organizer/gatherings/{gathering_id}/dashboard", headers=auth_headers
    ).json()["data"]
    assert len(visible_dashboard["participants"]) == 3
    early = client.post(
        f"/organizer/gatherings/{gathering_id}/attendance/u_demo_2",
        headers=auth_headers,
    )
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "CHECK_IN_WINDOW_CLOSED"
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.start_at = datetime.now(UTC) - timedelta(minutes=15)
        gathering.end_at = datetime.now(UTC) + timedelta(hours=2)
        db.commit()
    checked_in = client.post(
        f"/organizer/gatherings/{gathering_id}/attendance/u_demo_2",
        headers=auth_headers,
    )
    assert checked_in.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count(OrganizerAttendance.id)).where(
                OrganizerAttendance.gathering_id == gathering_id,
                OrganizerAttendance.user_id == "u_demo_2",
            )
        ) == 1
        assert db.scalar(
            select(func.count(TrustEvent.id)).where(
                TrustEvent.reference_id == gathering_id,
                TrustEvent.user_id == "u_demo_2",
                TrustEvent.event_type == "completion_confirmed",
            )
        ) == 0

    template = client.post(
        "/organizer/templates",
        headers=auth_headers,
        json={
            "title": "每周工作坊",
            "goal": "跨专业共创",
            "gathering_type": "workshop",
            "location": "创新空间",
            "campus": "珠海校区",
            "min_size": 3,
            "target_size": 12,
            "duration_minutes": 90,
            "recurrence_rule": "FREQ=WEEKLY",
        },
    )
    assert template.status_code == 201
    instantiated = client.post(
        f"/organizer/templates/{template.json()['data']['id']}/instantiate",
        headers=auth_headers,
        json={"start_at": (datetime.now(UTC) + timedelta(days=30)).isoformat()},
    )
    assert instantiated.status_code == 200
