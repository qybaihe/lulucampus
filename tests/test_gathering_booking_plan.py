from __future__ import annotations

from tests.test_intent_edit_and_capability import _confirmed_gathering


def test_confirmed_owner_selects_fresh_signed_room_option_before_preview(client):
    gathering_id = _confirmed_gathering(client)
    owner = {"X-User-ID": "u_demo_1"}

    denied = client.get(
        f"/gatherings/{gathering_id}/booking-options",
        headers={"X-User-ID": "u_demo_2"},
    )
    assert denied.status_code == 403

    options = client.get(
        f"/gatherings/{gathering_id}/booking-options", headers=owner
    )
    assert options.status_code == 200, options.text
    items = options.json()["data"]
    assert items
    option = items[0]
    assert option["action"] == "room.reserve_preview"
    assert option["resource_type"] == "room"
    assert option["location"].startswith("图书馆研讨室 15-")

    tampered = option["option_token"][:-1] + (
        "a" if option["option_token"][-1] != "a" else "b"
    )
    rejected = client.post(
        f"/gatherings/{gathering_id}/booking-plan",
        headers=owner,
        json={"option_token": tampered},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "BOOKING_OPTION_INVALID"

    selected = client.post(
        f"/gatherings/{gathering_id}/booking-plan",
        headers=owner,
        json={"option_token": option["option_token"]},
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["data"]["location"] == option["location"]

    capability = client.get(
        f"/gatherings/{gathering_id}/action-capability", headers=owner
    )
    assert capability.status_code == 200, capability.text
    action = capability.json()["data"]
    assert action["enabled"] is True
    assert action["action"] == "room.reserve_preview"
    assert action["params"]["room"] == "401"

    preview = client.post(
        "/actions/preview",
        headers=owner,
        json={
            "action": action["action"],
            "params": action["params"],
            "gathering_id": gathering_id,
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["status"] == "previewed"


def test_successful_action_remains_addressable_from_executed_gathering(client):
    """E6 result must survive the state transition so iOS can render it."""

    gathering_id = _confirmed_gathering(client)
    owner = {"X-User-ID": "u_demo_1"}
    options = client.get(
        f"/gatherings/{gathering_id}/booking-options", headers=owner
    ).json()["data"]
    selected = client.post(
        f"/gatherings/{gathering_id}/booking-plan",
        headers=owner,
        json={"option_token": options[0]["option_token"]},
    )
    assert selected.status_code == 200, selected.text
    capability = client.get(
        f"/gatherings/{gathering_id}/action-capability", headers=owner
    ).json()["data"]
    preview = client.post(
        "/actions/preview",
        headers=owner,
        json={
            "action": capability["action"],
            "params": capability["params"],
            "gathering_id": gathering_id,
        },
    ).json()["data"]
    for index in range(1, 5):
        authorized = client.post(
            f"/actions/{preview['id']}/authorization",
            headers={"X-User-ID": f"u_demo_{index}"},
            json={"authorized": True, "snapshot_hash": preview["snapshot_hash"]},
        )
        assert authorized.status_code == 200, authorized.text
    executed = client.post(
        "/actions/execute",
        headers=owner,
        json={"action_id": preview["id"], "params": capability["params"]},
    )
    assert executed.status_code == 200, executed.text
    detail = client.get(f"/gatherings/{gathering_id}", headers=owner)
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["status"] == "Executed"
    assert detail.json()["data"]["action_id"] == preview["id"]
