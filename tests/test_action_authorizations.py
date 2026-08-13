from __future__ import annotations

from tests.test_intent_edit_and_capability import _confirmed_gathering


def test_action_preview_requires_every_current_member_then_only_owner_executes(client):
    gathering_id = _confirmed_gathering(client)
    from datetime import UTC, datetime, timedelta

    from onemore.core.database import SessionLocal
    from onemore.db.models import Gathering

    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.gathering_type = "DDL冲刺"
        gathering.location = "图书馆研讨室 15-401"
        gathering.start_at = datetime.now(UTC) + timedelta(days=3)
        gathering.end_at = gathering.start_at + timedelta(hours=2)
        db.commit()

    owner = {"X-User-ID": "u_demo_1"}
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
    )
    assert preview.status_code == 200, preview.text
    action = preview.json()["data"]
    action_id = action["id"]
    assert action["authorization"] == {
        "required_count": 4,
        "authorized_count": 0,
        "actor_decision": "pending",
        "all_authorized": False,
    }
    premature = client.post(
        "/actions/execute",
        headers=owner,
        json={"action_id": action_id, "params": capability["params"]},
    )
    assert premature.status_code == 409
    assert premature.json()["error"]["code"] == "ACTION_AUTHORIZATION_INCOMPLETE"

    for index in range(1, 5):
        decision = client.post(
            f"/actions/{action_id}/authorization",
            headers={"X-User-ID": f"u_demo_{index}"},
            json={"authorized": True, "snapshot_hash": action["snapshot_hash"]},
        )
        assert decision.status_code == 200, decision.text
    peer_view = client.get(
        f"/actions/{action_id}", headers={"X-User-ID": "u_demo_2"}
    )
    assert peer_view.status_code == 200
    assert peer_view.json()["data"]["authorization"]["all_authorized"] is True
    peer_execute = client.post(
        "/actions/execute",
        headers={"X-User-ID": "u_demo_2"},
        json={"action_id": action_id, "params": capability["params"]},
    )
    assert peer_execute.status_code == 403
    executed = client.post(
        "/actions/execute",
        headers=owner,
        json={"action_id": action_id, "params": capability["params"]},
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["data"]["status"] == "succeeded"


def test_action_authorization_rejects_stale_snapshot_hash(client):
    # Contract-level stale hash defense is exercised through a directly seeded
    # preview by the companion end-to-end test; here a malformed 64-byte hash
    # cannot authorize a missing action and leaks no membership state.
    response = client.post(
        "/actions/not-found/authorization",
        headers={"X-User-ID": "u_demo_2"},
        json={"authorized": True, "snapshot_hash": "0" * 64},
    )
    assert response.status_code == 404


def _preview_for_modification(client) -> tuple[str, dict, dict]:
    gathering_id = _confirmed_gathering(client)
    from datetime import UTC, datetime, timedelta

    from onemore.core.database import SessionLocal
    from onemore.db.models import Gathering

    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.gathering_type = "DDL冲刺"
        gathering.location = "图书馆研讨室 15-401"
        gathering.start_at = datetime.now(UTC) + timedelta(days=3)
        gathering.end_at = gathering.start_at + timedelta(hours=2)
        db.commit()
    owner = {"X-User-ID": "u_demo_1"}
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
            "idempotency_key": f"preview-modification-{gathering_id}",
        },
    )
    assert preview.status_code == 200, preview.text
    return gathering_id, capability, preview.json()["data"]


def test_member_modification_invalidates_preview_and_all_prior_authorizations(client):
    gathering_id, capability, action = _preview_for_modification(client)
    owner = {"X-User-ID": "u_demo_1"}
    first_authorization = client.post(
        f"/actions/{action['id']}/authorization",
        headers=owner,
        json={"authorized": True, "snapshot_hash": action["snapshot_hash"]},
    )
    assert first_authorization.status_code == 200

    modified = client.post(
        f"/actions/{action['id']}/propose-modification",
        headers={"X-User-ID": "u_demo_2"},
        json={
            "snapshot_hash": action["snapshot_hash"],
            "reason": "希望改到东区研讨室，离下一节课更近",
            "proposed_params": {"room": "402"},
        },
    )
    assert modified.status_code == 200, modified.text
    data = modified.json()["data"]
    assert data["status"] == "invalidated"
    assert data["authorization"] == {
        "required_count": 4,
        "authorized_count": 0,
        "actor_decision": "invalidated",
        "all_authorized": False,
    }
    assert data["modification"] == {
        "reason": "希望改到东区研讨室，离下一节课更近",
        "proposed_params": {**action["params"], "room": "402"},
        "status": "requested",
        "created_at": data["modification"]["created_at"],
    }
    assert "requester_user_id" not in data["modification"]

    gathering = client.get(
        f"/gatherings/{gathering_id}", headers=owner
    ).json()["data"]
    assert gathering["status"] == "Confirmed"
    assert gathering["action_id"] is None
    stale_execute = client.post(
        "/actions/execute",
        headers=owner,
        json={"action_id": action["id"], "params": capability["params"]},
    )
    assert stale_execute.status_code == 409
    assert stale_execute.json()["error"]["code"] == "ACTION_NOT_EXECUTABLE"

    notifications = client.get(
        "/notifications", headers={"X-User-ID": "u_demo_3"}
    ).json()["data"]
    notice = next(
        item for item in notifications if item["type"] == "action_modification_requested"
    )
    assert {"requester_user_id", "proposed_by", "participants"}.isdisjoint(
        notice["payload"]
    )

    refreshed_capability = client.get(
        f"/gatherings/{gathering_id}/action-capability", headers=owner
    ).json()["data"]
    assert refreshed_capability["pending_modification"]["reason"] == (
        "希望改到东区研讨室，离下一节课更近"
    )
    assert refreshed_capability["pending_modification"]["proposed_params"]["room"] == "402"
    peer_capability = client.get(
        f"/gatherings/{gathering_id}/action-capability",
        headers={"X-User-ID": "u_demo_3"},
    )
    assert peer_capability.status_code == 200
    assert peer_capability.json()["data"]["enabled"] is False
    assert "requester_user_id" not in peer_capability.text
    regenerated = client.post(
        "/actions/preview",
        headers=owner,
        json={
            "action": refreshed_capability["action"],
            "params": refreshed_capability["pending_modification"]["proposed_params"],
            "gathering_id": gathering_id,
            "idempotency_key": f"revised-preview-{gathering_id}",
        },
    )
    assert regenerated.status_code == 200, regenerated.text
    assert regenerated.json()["data"]["id"] != action["id"]
    assert regenerated.json()["data"]["status"] == "previewed"
    assert regenerated.json()["data"]["params"]["room"] == "402"
    refreshed_after_apply = client.get(
        f"/gatherings/{gathering_id}/action-capability", headers=owner
    ).json()["data"]
    assert refreshed_after_apply["pending_modification"] is None


def test_authorization_decline_is_a_real_preview_modification_not_a_stuck_vote(client):
    gathering_id, _, action = _preview_for_modification(client)
    declined = client.post(
        f"/actions/{action['id']}/authorization",
        headers={"X-User-ID": "u_demo_4"},
        json={"authorized": False, "snapshot_hash": action["snapshot_hash"]},
    )
    assert declined.status_code == 200, declined.text
    assert declined.json()["data"]["status"] == "invalidated"
    assert declined.json()["data"]["modification"]["reason"] == "成员要求修改行动预览"
    gathering = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_4"}
    ).json()["data"]
    assert gathering["status"] == "Confirmed"


def test_overlap_template_authorization_explains_it_is_not_a_booking(client):
    from onemore.core.database import SessionLocal
    from onemore.db.models import CampusAction

    with SessionLocal() as db:
        action = CampusAction(
            user_id="u_demo_1",
            action_name="gym.book_preview",
            params={"venue_type": "羽毛球", "venue": "南校园"},
            preview_snapshot={"source": "peer_overlap_template"},
            snapshot_hash="d" * 64,
            idempotency_key="overlap-auth-not-booking",
        )
        db.add(action)
        db.commit()
        action_id = action.id
        snapshot_hash = action.snapshot_hash
    response = client.post(
        f"/actions/{action_id}/authorization",
        headers={"X-User-ID": "u_demo_1"},
        json={"authorized": True, "snapshot_hash": snapshot_hash},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "ACTION_NOT_AUTHORIZABLE"
    assert "时段参考" in response.json()["error"]["message"]
