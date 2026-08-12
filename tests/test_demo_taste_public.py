"""Public judge/demo taste entry — no App login required."""

from __future__ import annotations

import time


def _wait_status(client, headers, import_id, statuses, timeout=8.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        response = client.get(f"/profile/imports/{import_id}", headers=headers).json()[
            "data"
        ]
        last = response
        if response["status"] in statuses:
            return response
        time.sleep(0.05)
    raise AssertionError(
        f"status never reached {statuses}; last={last and last['status']}"
    )


def test_demo_taste_status(client):
    response = client.get("/demo/taste/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["enabled"] is True
    assert data["mode"] in {"fake", "browser"}


def test_demo_taste_qr_bootstraps_guest_and_reaches_ready(client, monkeypatch):
    # Force fake provider for deterministic CI / local unit path.
    monkeypatch.setenv("ONEMORE_DOUYIN_MODE", "fake")
    from onemore.core.config import get_settings

    get_settings.cache_clear()

    start = client.post(
        "/demo/taste/douyin/qr?wait_seconds=8",
        json={"max_items": 0, "force": True},
    )
    assert start.status_code == 202, start.text
    payload = start.json()["data"]
    assert payload["access_token"].startswith("om1.")
    assert payload["guest_user_id"].startswith("guest_")
    assert payload["import_id"]
    assert payload["qr_image_data_url"] or payload["status"] == "PREPARING_QR"

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    # Unauthenticated poll must fail
    bare = client.get(f"/profile/imports/{payload['import_id']}")
    assert bare.status_code == 401

    data = _wait_status(
        client,
        headers,
        payload["import_id"],
        {"READY", "FAILED", "CANCELLED", "WAITING_SCAN", "AUTHENTICATED"},
        timeout=12.0,
    )
    # Fake provider completes quickly after scan simulation in background.
    if data["status"] != "READY":
        data = _wait_status(
            client, headers, payload["import_id"], {"READY"}, timeout=20.0
        )
    assert data["status"] == "READY"
    assert data["result"] is not None
    assert data["result"]["primary_tag"]["key"]

    # Guest token cannot read a different user's import.
    denied = client.get("/profile/imports/imp_not_owned_by_guest", headers=headers)
    assert denied.status_code == 404
