from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import Notification, PushDelivery, PushDevice
from onemore.modules.notify import service as notify_service
from onemore.modules.notify.service import apns_payload, decrypt_device_token, push


def test_apns_token_transfers_between_accounts_and_can_be_deactivated(client):
    token = "a" * 64
    first = {"X-User-ID": "u_demo_1"}
    second = {"X-User-ID": "u_demo_2"}
    assert client.post(
        "/notifications/devices", headers=first, json={"token": token, "platform": "ios"}
    ).status_code == 201
    assert client.post(
        "/notifications/devices", headers=second, json={"token": token, "platform": "ios"}
    ).status_code == 201

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with SessionLocal() as db:
        devices = list(
            db.scalars(select(PushDevice).where(PushDevice.token_hash == token_hash))
        )
        assert len(devices) == 1
        assert devices[0].user_id == "u_demo_2"
        assert devices[0].active is True

    removed = client.request(
        "DELETE", "/notifications/devices", headers=second, json={"token": token}
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["data"] == {"active": False, "deactivated": 1}
    with SessionLocal() as db:
        assert not db.scalar(
            select(PushDevice.active).where(
                PushDevice.user_id == "u_demo_2", PushDevice.token_hash == token_hash
            )
        )


def test_installation_proof_survives_session_expiry_but_not_account_transfer(client):
    token = "b" * 64
    first = {"X-User-ID": "u_demo_1"}
    second = {"X-User-ID": "u_demo_2"}
    registered_first = client.post(
        "/notifications/devices", headers=first, json={"token": token, "platform": "ios"}
    )
    first_proof = registered_first.json()["data"]["deactivation_token"]

    deactivated = client.request(
        "DELETE",
        "/notifications/devices/installation",
        json={"token": token, "deactivation_token": first_proof},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["data"]["deactivated"] == 1

    registered_second = client.post(
        "/notifications/devices", headers=second, json={"token": token, "platform": "ios"}
    )
    second_proof = registered_second.json()["data"]["deactivation_token"]
    stale = client.request(
        "DELETE",
        "/notifications/devices/installation",
        json={"token": token, "deactivation_token": first_proof},
    )
    assert stale.status_code == 200
    assert stale.json()["data"]["deactivated"] == 0
    current = client.request(
        "DELETE",
        "/notifications/devices/installation",
        json={"token": token, "deactivation_token": second_proof},
    )
    assert current.status_code == 200
    assert current.json()["data"]["deactivated"] == 1


def test_encrypted_token_fake_provider_delivery_and_route_payload(client):
    token = "device-token-never-stored-in-plaintext-1234567890"
    headers = {"X-User-ID": "u_demo_1"}
    registered = client.post(
        "/notifications/devices",
        headers=headers,
        json={"token": token, "platform": "ios"},
    )
    assert registered.status_code == 201

    with SessionLocal() as db:
        device = db.scalar(select(PushDevice).where(PushDevice.user_id == "u_demo_1"))
        assert device is not None
        assert device.token_ciphertext is not None
        assert token not in device.token_ciphertext
        assert device.token_key_id
        assert decrypt_device_token(device) == token
        notification = push(
            db,
            "u_demo_1",
            "confirmation_required",
            {
                "summary": "请确认周六羽毛球组局",
                "gathering_id": "g-fixture",
                "deep_link": "onemore://gathering/g-fixture/confirm",
            },
            dedupe_key="fixture-confirmation",
        )
        db.commit()
        delivery = db.scalar(
            select(PushDelivery).where(PushDelivery.notification_id == notification.id)
        )
        assert delivery is not None
        assert delivery.status == "delivered"
        assert delivery.provider_status == 200
        db.refresh(notification)
        assert notification.delivered_at is not None
        payload = apns_payload(notification)
        assert payload["gathering_id"] == "g-fixture"
        assert payload["deep_link"].endswith("/confirm")
        assert payload["type"] == "confirmation_required"
        assert token not in str(payload)

    exported = client.get("/me/data-export", headers=headers).text
    assert token not in exported
    assert "token_ciphertext" not in exported


def test_apns_410_deactivates_installation_and_preferences_skip_provider(client):
    gone_token = "fake:gone:" + "x" * 32
    headers = {"X-User-ID": "u_demo_1"}
    assert (
        client.post(
            "/notifications/devices",
            headers=headers,
            json={"token": gone_token, "platform": "ios"},
        ).status_code
        == 201
    )
    with SessionLocal() as db:
        gone = push(
            db,
            "u_demo_1",
            "competition_deadline",
            {"summary": "报名即将截止", "competition_id": "competition-fixture"},
        )
        db.commit()
        delivery = db.scalar(
            select(PushDelivery).where(PushDelivery.notification_id == gone.id)
        )
        assert delivery is not None
        assert delivery.status == "invalidated"
        assert delivery.provider_status == 410
        device = db.scalar(select(PushDevice).where(PushDevice.user_id == "u_demo_1"))
        assert device is not None and device.active is False

    live_token = "fake:live:" + "y" * 32
    assert (
        client.post(
            "/notifications/devices",
            headers=headers,
            json={"token": live_token, "platform": "ios"},
        ).status_code
        == 201
    )
    assert (
        client.patch(
            "/me/notification-preferences",
            headers=headers,
            json={"categories": {"chat_messages": False}},
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        suppressed = push(
            db,
            "u_demo_1",
            "chat_message",
            {"summary": "会话有新消息", "channel_id": "channel-fixture"},
        )
        db.commit()
        assert db.scalar(
            select(PushDelivery).where(PushDelivery.notification_id == suppressed.id)
        ) is None
        stored = db.get(Notification, suppressed.id)
        assert stored is not None
        assert stored.payload["push_delivery_suppressed"] is True


def test_provider_failure_never_fails_business_commit_and_retries_are_bounded(
    client, monkeypatch
):
    headers = {"X-User-ID": "u_demo_1"}
    token = "fake:error-boundary:" + "z" * 32
    assert (
        client.post(
            "/notifications/devices",
            headers=headers,
            json={"token": token, "platform": "ios"},
        ).status_code
        == 201
    )

    class ExplodingProvider:
        def send(self, token: str, payload: dict):
            del token, payload
            raise httpx.ConnectError("fixture provider is offline")

    monkeypatch.setattr(notify_service, "get_push_provider", lambda: ExplodingProvider())
    with SessionLocal() as db:
        notification = push(
            db,
            "u_demo_1",
            "gathering_reminder",
            {"gathering_id": "g-outbox", "deep_link": "onemore://gathering/g-outbox"},
        )
        # The after-commit delivery hook sees the provider failure, but the
        # authoritative notification/business transaction remains successful.
        db.commit()

    for expected_attempt in range(1, 6):
        with SessionLocal() as db:
            delivery = db.scalar(
                select(PushDelivery).where(
                    PushDelivery.notification_id == notification.id
                )
            )
            assert delivery is not None
            if delivery.attempt_count < expected_attempt:
                delivery.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
                db.commit()
                notify_service.drain_push_outbox(db)

    with SessionLocal() as db:
        delivery = db.scalar(
            select(PushDelivery).where(PushDelivery.notification_id == notification.id)
        )
        assert delivery is not None
        assert delivery.attempt_count == 5
        assert delivery.status == "failed"
        assert delivery.provider_reason == "ProviderUnavailable"
        assert db.get(Notification, notification.id) is not None
