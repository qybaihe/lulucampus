from __future__ import annotations

from datetime import UTC, datetime, timedelta

from onemore.core.database import SessionLocal
from onemore.db.models import Gathering, GatheringStatus, IntentCard, IntentStatus


def _draft(client, user_id: str = "u_demo_1") -> tuple[dict, str]:
    headers = {"X-User-ID": user_id}
    response = client.post(
        "/intent/compile",
        headers=headers,
        json={"text": "周六晚上珠海校区一起打羽毛球，3个人"},
    )
    assert response.status_code == 200
    return headers, response.json()["data"]["card"]["id"]


def _published_gathering(client, user_id: str = "u_demo_1") -> tuple[dict, str]:
    headers, card_id = _draft(client, user_id)
    published = client.post(
        "/intent/publish", headers=headers, json={"card_id": card_id}
    )
    assert published.status_code == 201, published.text
    return headers, published.json()["data"]["gathering_id"]


def _expire_gathering(gathering_id: str) -> None:
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()


def test_expired_draft_cannot_publish(client):
    headers, card_id = _draft(client)
    with SessionLocal() as db:
        card = db.get(IntentCard, card_id)
        assert card is not None
        card.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    response = client.post(
        "/intent/publish", headers=headers, json={"card_id": card_id}
    )
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "INTENT_EXPIRED"
    with SessionLocal() as db:
        assert db.get(IntentCard, card_id).status == IntentStatus.EXPIRED.value


def test_expired_pool_is_hidden_and_join_fails_closed_inside_lock(client):
    _, gathering_id = _published_gathering(client)
    _expire_gathering(gathering_id)
    visible_ids = {
        item["id"]
        for item in client.get(
            "/gatherings/open", headers={"X-User-ID": "u_demo_2"}
        ).json()["data"]
    }
    assert gathering_id not in visible_ids
    joined = client.post(
        f"/gatherings/{gathering_id}/join",
        headers={"X-User-ID": "u_demo_2"},
        json={},
    )
    assert joined.status_code == 410
    assert joined.json()["error"]["code"] == "GATHERING_EXPIRED"
    with SessionLocal() as db:
        assert db.get(Gathering, gathering_id).status == GatheringStatus.DISSOLVED.value


def test_expired_pool_cannot_issue_share_or_form_in_matching(client, admin_headers):
    owner, share_gathering_id = _published_gathering(client)
    _expire_gathering(share_gathering_id)
    share = client.post(
        f"/gatherings/{share_gathering_id}/share", headers=owner
    )
    assert share.status_code == 410

    _, matching_gathering_id = _published_gathering(client, "u_demo_1")
    _expire_gathering(matching_gathering_id)
    _published_gathering(client, "u_demo_2")
    _published_gathering(client, "u_demo_3")
    run = client.post("/internal/matching/run", headers=admin_headers)
    assert run.status_code == 200
    with SessionLocal() as db:
        assert (
            db.get(Gathering, matching_gathering_id).status
            == GatheringStatus.DISSOLVED.value
        )


def test_expired_official_pool_at_minimum_enters_confirmation(client):
    owner, gathering_id = _published_gathering(client)
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.is_official = True
        gathering.min_size = 1
        gathering.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

    response = client.post(f"/gatherings/{gathering_id}/share", headers=owner)
    assert response.status_code == 410
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        assert gathering.status == GatheringStatus.TENTATIVE.value
        assert gathering.confirmation_deadline is not None
