from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from onemore.core.database import SessionLocal
from onemore.db.models import ExternalEvent


def test_public_events_emit_rfc3339_utc_for_sqlite_naive_datetimes(
    client: TestClient,
) -> None:
    event = ExternalEvent(
        id="guest-rfc3339-event",
        source="lecture",
        external_key="guest-rfc3339-event",
        title="公开讲座",
        starts_at=datetime(2026, 8, 14, 12, 18, 33, 612990),
        ends_at=datetime(2026, 8, 14, 14, 18, 33, 612990),
        location="东校园",
        official_url="https://example.edu.cn/events/guest-rfc3339-event",
        details={},
    )
    with SessionLocal() as db:
        db.add(event)
        db.commit()

    response = client.get("/events")
    assert response.status_code == 200
    row = next(item for item in response.json()["data"] if item["id"] == event.id)
    assert row["starts_at"].endswith("Z")
    assert row["ends_at"].endswith("Z")

    detail = client.get(f"/events/{event.id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["starts_at"].endswith("Z")


def test_user_event_publish_requires_t4(client, auth_headers) -> None:
    """用户发布校园活动：T1 拒绝（TRUST_LEVEL_REQUIRED），T4 放行且匿名呈现。"""
    from onemore.db.models import TrustProfile

    def set_level(level: str) -> None:
        with SessionLocal() as db:
            profile = db.get(TrustProfile, "u_demo_1")
            assert profile is not None
            profile.level = level
            profile.organizer_verified = level == "T4"
            db.commit()

    payload = {
        "title": "周末飞盘体验课",
        "type": "体育",
        "starts_at": "2026-08-16T10:00:00Z",
        "location": "珠海校区体育馆",
        "description": "零基础友好，自带水杯",
    }

    set_level("T1")
    denied = client.post("/events", headers=auth_headers, json=payload)
    assert denied.status_code == 403
    assert denied.json()["error"]["details"]["capability"] == "campus_event_publish"

    set_level("T4")
    created = client.post("/events", headers=auth_headers, json=payload)
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["title"] == "周末飞盘体验课"
    assert data["details"]["publisher"] == "user"
    assert "u_demo_1" not in str(data)

    listed = client.get("/events")
    assert listed.status_code == 200
    row = next(item for item in listed.json()["data"] if item["id"] == data["id"])
    assert row["details"]["publisher"] == "user"

    set_level("T1")
