from __future__ import annotations

from datetime import UTC, datetime

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Channel,
    ChannelStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    Relation,
    RelationStatus,
    SessionHealth,
)
from onemore.modules.collab import service as collab_service


def test_async_login_session_and_read_only_identity(client):
    created = client.post("/auth/session", json={})
    assert created.status_code == 202
    data = created.json()["data"]
    redemption = {"X-Login-Redemption": data["redemption_token"]}
    assert data["status"] == "WAITING_SCAN"
    assert data["qr_image_data_url"].startswith("data:image/")
    completed = client.post(
        f"/auth/session/{data['id']}/demo-complete", headers=redemption
    )
    assert completed.status_code == 200
    polled = client.get(
        f"/auth/session/{data['id']}", headers=redemption
    ).json()["data"]
    assert polled["status"] == "SUCCESS"
    paths = client.get("/openapi.json").json()["paths"]
    assert "/auth/identity" not in paths
    assert "patch" not in paths["/auth/me"]
    assert "patch" in paths["/me/display-name"]


def test_identity_session_health_datetimes_are_rfc3339_utc(client, auth_headers):
    """SQLite drops tzinfo; the typed response contract must restore UTC."""
    with SessionLocal() as db:
        db.add(
            SessionHealth(
                user_id="u_demo_1",
                subsystem="rfc3339-contract",
                healthy=True,
                last_checked_at=datetime(2026, 8, 11, 22, 34, 3, 212720),
            )
        )
        db.commit()

    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    item = next(
        value
        for value in response.json()["data"]["session_health"]
        if value["subsystem"] == "rfc3339-contract"
    )
    serialized = item["last_checked_at"]
    assert serialized is not None
    parsed = datetime.fromisoformat(serialized.replace("Z", "+00:00"))
    assert parsed.utcoffset() is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_revoke_timetable_cascades_free_windows_and_pool(client, auth_headers):
    card = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={"text": "找人一起自习"},
    ).json()["data"]["card"]
    client.post("/intent/publish", headers=auth_headers, json={"card_id": card["id"]})
    assert client.get("/schedule/free-windows", headers=auth_headers).json()["data"]
    revoked = client.post(
        "/auth/grants",
        headers=auth_headers,
        json={"scope": "timetable", "granted": False},
    )
    assert revoked.status_code == 200
    assert client.get("/schedule/free-windows", headers=auth_headers).json()["data"] == []
    intent = client.get(f"/intent/{card['id']}", headers=auth_headers).json()["data"]
    assert intent["status"] == "Withdrawn"


def test_relation_dissolve_is_silent_for_both_sides(client):
    headers_one = {"X-User-ID": "u_demo_1"}
    relations = client.get("/relations", headers=headers_one).json()["data"]
    relation = next(
        item
        for item in relations
        if any(participant["user_id"] == "u_demo_2" for participant in item["participants"])
    )
    deleted = client.delete(f"/relations/{relation['id']}", headers=headers_one)
    assert deleted.status_code == 200
    assert deleted.json()["data"]["notified"] is False
    for user_id in ("u_demo_1", "u_demo_2"):
        response = client.get(f"/relations/{relation['id']}", headers={"X-User-ID": user_id})
        assert response.status_code == 404
    notifications = client.get("/notifications", headers={"X-User-ID": "u_demo_2"}).json()["data"]
    assert not any(item["type"] == "relation_dissolved" for item in notifications)


def test_new_shared_experience_reopens_reactivated_relation_channel(client):
    headers = {"X-User-ID": "u_demo_1"}
    relation_view = next(
        item
        for item in client.get("/relations", headers=headers).json()["data"]
        if any(participant["user_id"] == "u_demo_2" for participant in item["participants"])
    )
    relation_id = relation_view["id"]
    channel_id = relation_view["channel_id"]
    assert client.delete(f"/relations/{relation_id}", headers=headers).status_code == 200

    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="复局回归测试",
            title="新共同经历",
            goal="验证关系与通道原子重开",
            status=GatheringStatus.COMPLETED.value,
            completed_at=datetime.now(UTC),
        )
        db.add(gathering)
        db.flush()
        db.add_all(
            [
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user_id,
                    completion_confirmed=True,
                )
                for user_id in ("u_demo_1", "u_demo_2")
            ]
        )
        db.flush()
        collab_service.record_experience(db, gathering.id)
        db.commit()
        relation = db.get(Relation, relation_id)
        channel = db.get(Channel, channel_id)
        assert relation is not None and relation.status == RelationStatus.ACTIVE.value
        assert channel is not None and channel.status == ChannelStatus.OPEN.value

    sent = client.post(
        f"/channels/{channel_id}/messages",
        headers=headers,
        json={"content_type": "text", "content": "新的共同经历后重新开始对话"},
    )
    assert sent.status_code == 201, sent.text


def test_shared_experience_contract_contains_facts_only(client, auth_headers):
    relation = client.get("/relations", headers=auth_headers).json()["data"][0]
    assert relation["experiences"]
    for experience in relation["experiences"]:
        assert set(experience) == {
            "id",
            "participants",
            "gathering_type",
            "occurred_at",
            "outcome",
            "common_grounds",
        }
        assert {"rating", "impression", "tags", "note"}.isdisjoint(experience)
