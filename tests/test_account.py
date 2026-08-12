from __future__ import annotations

import base64
from pathlib import Path

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import ChannelParticipant, MediaAsset, MediaChannelGrant


def test_block_management_has_no_user_discovery(client, auth_headers):
    blocked = client.post("/me/blocks/u_demo_2", headers=auth_headers)
    assert blocked.status_code == 201
    items = client.get("/me/blocks", headers=auth_headers).json()["data"]
    assert any(item["blocked_user_id"] == "u_demo_2" for item in items)
    removed = client.delete("/me/blocks/u_demo_2", headers=auth_headers)
    assert removed.status_code == 200
    assert not any(
        item["blocked_user_id"] == "u_demo_2"
        for item in client.get("/me/blocks", headers=auth_headers).json()["data"]
    )


def test_data_export_excludes_auth_secrets(client, auth_headers):
    exported = client.get("/me/data-export", headers=auth_headers)
    assert exported.status_code == 200
    text = exported.text
    assert "netid_hash" not in text
    assert "token_hash" not in text
    assert "token_ciphertext" not in text
    assert "cookie" not in text
    assert exported.json()["data"]["identity"]["user_id"] == "u_demo_1"


def test_account_deactivation_invalidates_identity(client):
    headers = {"X-User-ID": "u_demo_4"}
    deleted = client.request(
        "DELETE",
        "/me/account",
        headers=headers,
        json={"confirmation": "DELETE"},
    )
    assert deleted.status_code == 200, deleted.text
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_account_deactivation_revokes_and_deletes_uploaded_media(client):
    owner = {"X-User-ID": "u_demo_4"}
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    uploaded = client.post(
        "/media/images",
        headers={**owner, "Content-Type": "image/png", "X-Filename": "private.png"},
        content=png,
    )
    assert uploaded.status_code == 201, uploaded.text
    media_id = uploaded.json()["data"]["media_id"]

    with SessionLocal() as db:
        asset = db.get(MediaAsset, media_id)
        assert asset is not None
        stored_path = Path(asset.storage_path)
        participant = db.scalar(
            select(ChannelParticipant).where(ChannelParticipant.user_id == "u_demo_4")
        )
        assert participant is not None
        peer_id = db.scalar(
            select(ChannelParticipant.user_id).where(
                ChannelParticipant.channel_id == participant.channel_id,
                ChannelParticipant.user_id != "u_demo_4",
            )
        )
        assert peer_id is not None
        db.add(MediaChannelGrant(media_id=media_id, channel_id=participant.channel_id))
        db.commit()

    peer = {"X-User-ID": peer_id}
    assert client.get(f"/media/images/{media_id}", headers=peer).status_code == 200
    deleted = client.request(
        "DELETE", "/me/account", headers=owner, json={"confirmation": "DELETE"}
    )
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/media/images/{media_id}", headers=peer).status_code == 404
    assert not stored_path.exists()
    with SessionLocal() as db:
        assert db.get(MediaAsset, media_id) is None
        assert not list(
            db.scalars(
                select(MediaChannelGrant).where(MediaChannelGrant.media_id == media_id)
            )
        )
