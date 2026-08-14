from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.demo_cast import LIVE_TEST_PHONES
from onemore.db.models import User
from onemore.db.peer_overlap import attach_live_test_users, seed_live_partner_chats, seed_relation_chat_previews
from onemore.modules.profile.service import init_profile
from onemore.modules.trust.service import ensure_trust_profile


def test_demo_relations_include_chat_preview(client, auth_headers):
    with SessionLocal() as db:
        seed_relation_chat_previews(db)
    listed = client.get("/relations", headers=auth_headers).json()["data"]
    assert listed
    with_preview = [item for item in listed if item.get("last_message")]
    assert with_preview
    assert with_preview[0]["peer_display_name"]
    assert with_preview[0]["last_message"]["content"]
    assert with_preview[0]["channel_id"]


def test_live_test_phone_gets_cast_partner_chats(client):
    phone = LIVE_TEST_PHONES[0]
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.phone == phone))
        if existing is None:
            user = User(
                phone=phone,
                display_name="白鹤",
                social_enabled=True,
                verified_at=datetime.now(UTC),
                account_status="active",
            )
            db.add(user)
            db.flush()
            init_profile(db, user.id)
            ensure_trust_profile(db, user.id)
            db.commit()
            user_id = user.id
        else:
            user_id = existing.id
        attach_live_test_users(db)

    listed = client.get("/relations", headers={"X-User-ID": user_id}).json()["data"]
    names = {item.get("peer_display_name") for item in listed}
    assert {"林予安", "陈可薇", "梁景行", "何屿"} <= names
    assert all(item.get("last_message") for item in listed)
    assert all(item.get("channel_id") for item in listed)

    lin = next(item for item in listed if item["peer_display_name"] == "林予安")
    messages = client.get(
        f"/channels/{lin['channel_id']}/messages",
        headers={"X-User-ID": user_id},
    ).json()["data"]
    texts = [item.get("content") for item in messages]
    assert any("英东" in (text or "") for text in texts)
    assert len(messages) >= 3
    human_names = {
        item.get("sender_display_name")
        for item in messages
        if item.get("sender_type") == "human" and item.get("sender_id") != user_id
    }
    assert "林予安" in human_names

    header = client.get(
        f"/channels/{lin['channel_id']}",
        headers={"X-User-ID": user_id},
    ).json()["data"]
    assert header["kind"] == "relation"
    assert header["title"] == "林予安"
    assert header["relation_id"] == lin["id"]
    assert "一起" in (header["subtitle"] or "")
    assert client.get(
        f"/channels/{lin['channel_id']}",
        headers={"X-User-ID": "u_demo_3"},
    ).status_code == 403

    with SessionLocal() as db:
        seed_live_partner_chats(db)
    lin_messages = client.get(
        f"/channels/{lin['channel_id']}/messages",
        headers={"X-User-ID": user_id},
    ).json()["data"]
    assert [item.get("content") for item in lin_messages].count(
        "下次还是英东吧，我可以再订一场。"
    ) == 1
