from __future__ import annotations

from datetime import date

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import SecurityEvent
from onemore.hermes.catalog import build_argv
from onemore.hermes.schemas import ActionName, RoomReserveParams


def _confirmed_gathering(client):
    compiled = {}
    for index in range(1, 5):
        headers = {"X-User-ID": f"u_demo_{index}"}
        card = client.post(
            "/intent/compile",
            headers=headers,
            json={"text": "周六晚上一起打羽毛球，4人"},
        ).json()["data"]["card"]
        compiled[index] = card
        assert (
            client.post(
                "/intent/publish", headers=headers, json={"card_id": card["id"]}
            ).status_code
            == 201
        )
    run = client.post("/internal/matching/run", headers={"X-Admin-Token": "test-admin"})
    assert run.status_code == 200
    gathering_id = run.json()["data"]["gathering_ids"][0]
    for index in range(1, 5):
        response = client.post(
            f"/gatherings/{gathering_id}/confirm",
            headers={"X-User-ID": f"u_demo_{index}"},
            json={"confirmed": True},
        )
        assert response.status_code == 200
    detail = client.get(f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_1"}).json()[
        "data"
    ]
    assert detail["status"] == "Confirmed"
    assert detail["channel_id"]
    return gathering_id, detail["channel_id"]


def test_confirm_flag_only_comes_from_server():
    params = RoomReserveParams(
        kind="15",
        room="401",
        date=date(2026, 8, 20),
        start="19:00",
        end="21:00",
        members=["24330001"],
    )
    without = build_argv(ActionName.ROOM_RESERVE_COMMIT, params, server_confirmed=False)
    with_confirm = build_argv(ActionName.ROOM_RESERVE_COMMIT, params, server_confirmed=True)
    assert "--confirm" not in without
    assert "--confirm" in with_confirm
    assert all(isinstance(part, str) for part in with_confirm)


def test_hermes_natural_room_booking_clarifies_then_returns_complete_preview(
    client, auth_headers
):
    incomplete = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={"text": "帮我预约研讨室"},
    )
    assert incomplete.status_code == 200, incomplete.text
    clarification = incomplete.json()["data"]
    assert clarification["kind"] == "clarification"
    assert clarification["requires_preview"] is False
    assert clarification["action"] == "room.reserve_preview"
    assert set(clarification["data"]["required_fields"]) == {
        "kind",
        "room",
        "date",
        "start",
        "end",
    }
    assert clarification["data"]["form_screen"] == "B6"

    complete = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={
            "text": "帮我预约研讨室",
            "context": {
                "kind": "15",
                "room": "402",
                "date": "2026-08-20",
                "start": "19:00",
                "end": "21:00",
                "members": [],
                "services": [],
            },
        },
    )
    assert complete.status_code == 200, complete.text
    result = complete.json()["data"]
    assert result["kind"] == "action_preview"
    assert result["requires_preview"] is True
    assert result["action"] == "room.reserve_preview"
    assert result["data"]["params"]["room"] == "402"
    assert result["data"]["params"]["members"] == []


def test_hermes_today_placeholder_routes_to_course_list(client, auth_headers):
    response = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={"text": "今天有什么课？"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["card_type"] == "course_list"


def test_preview_execute_and_human_chat_end_to_end(client):
    gathering_id, channel_id = _confirmed_gathering(client)
    owner = {"X-User-ID": "u_demo_1"}
    params = {
        "kind": "15",
        "room": "401",
        "date": "2026-08-20",
        "start": "19:00",
        "end": "21:00",
        "members": ["u_demo_2", "u_demo_3", "u_demo_4"],
        "title": "羽毛球复盘",
        "memo": "共同活动",
        "services": [],
    }
    preview = client.post(
        "/actions/preview",
        headers=owner,
        json={
            "action": "room.reserve_preview",
            "params": params,
            "gathering_id": gathering_id,
            "confirm": True,
        },
    )
    assert preview.status_code == 200, preview.text
    action = preview.json()["data"]
    assert action["status"] == "previewed"
    mismatch = client.post(
        "/actions/execute",
        headers=owner,
        json={"action_id": action["id"], "params": {**params, "room": "402"}},
    )
    assert mismatch.status_code == 409
    blocked = client.post(
        "/actions/execute",
        headers=owner,
        json={"action_id": action["id"], "params": params, "confirm": True},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "ACTION_AUTHORIZATION_INCOMPLETE"
    for index in range(1, 5):
        authorized = client.post(
            f"/actions/{action['id']}/authorization",
            headers={"X-User-ID": f"u_demo_{index}"},
            json={"authorized": True, "snapshot_hash": action["snapshot_hash"]},
        )
        assert authorized.status_code == 200, authorized.text
    executed = client.post(
        "/actions/execute",
        headers=owner,
        json={"action_id": action["id"], "params": params, "confirm": True},
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["data"]["status"] == "succeeded"
    detail = client.get(f"/gatherings/{gathering_id}", headers=owner).json()["data"]
    assert detail["status"] == "Executed"

    first = client.post(
        f"/channels/{channel_id}/messages",
        headers=owner,
        json={"content": "周六见", "content_type": "text"},
    )
    second = client.post(
        f"/channels/{channel_id}/messages",
        headers={"X-User-ID": "u_demo_2"},
        json={"content": "我会提前到", "content_type": "text"},
    )
    assert first.status_code == second.status_code == 201
    messages = client.get(f"/channels/{channel_id}/messages", headers=owner).json()["data"]
    assert all("read_at" not in message for message in messages)
    assert {message["sender_type"] for message in messages} >= {"human", "azou"}
    with SessionLocal() as db:
        event_types = set(db.scalars(select(SecurityEvent.event_type)))
    assert {"client_confirm_discarded", "preview_params_mismatch"} <= event_types


def test_client_cannot_request_commit_action(client, auth_headers):
    response = client.post(
        "/actions/preview",
        headers=auth_headers,
        json={
            "action": "room.reserve_commit",
            "params": {
                "kind": "15",
                "room": "401",
                "date": "2026-08-20",
                "start": "19:00",
                "end": "21:00",
            },
        },
    )
    assert response.status_code == 403


def test_personal_yellow_action_requires_preview_and_self_authorization(client, auth_headers):
    response = client.post(
        "/actions/preview",
        headers=auth_headers,
        json={
            "action": "room.reserve_preview",
            "params": {
                "kind": "15",
                "room": "401",
                "date": "2026-08-20",
                "start": "19:00",
                "end": "21:00",
            },
        },
    )
    assert response.status_code == 200, response.text
    action = response.json()["data"]
    assert action["authorization"] == {
        "required_count": 1,
        "authorized_count": 0,
        "actor_decision": "pending",
        "all_authorized": False,
    }
    blocked = client.post(
        "/actions/execute",
        headers=auth_headers,
        json={"action_id": action["id"], "params": action["params"]},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "ACTION_AUTHORIZATION_INCOMPLETE"
    authorized = client.post(
        f"/actions/{action['id']}/authorization",
        headers=auth_headers,
        json={"authorized": True, "snapshot_hash": action["snapshot_hash"]},
    )
    assert authorized.status_code == 200, authorized.text
    assert authorized.json()["data"]["authorization"]["all_authorized"] is True
    executed = client.post(
        "/actions/execute",
        headers=auth_headers,
        json={"action_id": action["id"], "params": action["params"]},
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["data"]["status"] == "succeeded"


def test_action_with_other_members_still_requires_confirmed_gathering(client, auth_headers):
    response = client.post(
        "/actions/preview",
        headers=auth_headers,
        json={
            "action": "room.reserve_preview",
            "params": {
                "kind": "15",
                "room": "401",
                "date": "2026-08-20",
                "start": "19:00",
                "end": "21:00",
                "members": ["u_demo_2"],
            },
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "GATHERING_REQUIRED"
