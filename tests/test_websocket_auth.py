from __future__ import annotations

import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from onemore.core.auth import issue_access_token
from onemore.core.database import SessionLocal
from onemore.db.models import Channel, ChannelParticipant, ChannelStatus


def _channel_for(user_id: str) -> str:
    with SessionLocal() as db:
        channel_id = db.scalar(
            select(ChannelParticipant.channel_id).where(ChannelParticipant.user_id == user_id)
        )
    assert channel_id is not None
    return channel_id


def test_websocket_authenticates_with_header_and_never_requires_query_token(client):
    channel_id = _channel_for("u_demo_1")
    token = issue_access_token("u_demo_1")
    with client.websocket_connect(
        f"/channels/{channel_id}", headers={"Authorization": f"Bearer {token}"}
    ) as socket:
        socket.send_json({"content": "header-auth", "content_type": "text"})
        payload = socket.receive_json()
        assert payload["content"] == "header-auth"

    # A legacy token in the query string is deliberately ignored so access
    # logs, proxies, and APM URLs can never capture a reusable credential.
    with (
        pytest.raises(WebSocketDisconnect) as caught,
        client.websocket_connect(f"/channels/{channel_id}?token={token}"),
    ):
        pass
    assert caught.value.code == 4401


def test_existing_socket_is_reauthorized_before_three_person_broadcast(client):
    with SessionLocal() as db:
        channel = Channel(status=ChannelStatus.OPEN.value)
        db.add(channel)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
            db.add(ChannelParticipant(channel_id=channel.id, user_id=user_id))
        db.commit()
        channel_id = channel.id

    token = issue_access_token("u_demo_1")
    with client.websocket_connect(
        f"/channels/{channel_id}", headers={"Authorization": f"Bearer {token}"}
    ) as socket:
        assert (
            client.post(
                "/me/blocks/u_demo_2", headers={"X-User-ID": "u_demo_1"}
            ).status_code
            == 201
        )
        sent = client.post(
            f"/channels/{channel_id}/messages",
            headers={"X-User-ID": "u_demo_3"},
            json={"content": "third-party-after-block", "content_type": "text"},
        )
        assert sent.status_code == 201
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4403

    notifications = client.get(
        "/notifications", headers={"X-User-ID": "u_demo_1"}
    ).json()["data"]
    assert not any(
        item["type"] == "chat_message"
        and item["payload"].get("channel_id") == channel_id
        for item in notifications
    )
