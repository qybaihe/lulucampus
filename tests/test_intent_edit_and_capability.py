from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from onemore.core.database import SessionLocal
from onemore.db.models import Gathering, GatheringStatus, TimeWindow


def test_clarification_questions_have_stable_keys_and_answers_are_consumed(client):
    headers = {"X-User-ID": "u_demo_1"}
    with SessionLocal() as db:
        db.execute(delete(TimeWindow).where(TimeWindow.user_id == "u_demo_1"))
        db.commit()
    first = client.post(
        "/intent/compile", headers=headers, json={"text": "想组一个项目团队"}
    )
    assert first.status_code == 200, first.text
    questions = first.json()["data"]["questions"]
    assert {item["key"] for item in questions} == {"availability", "required_roles"}
    assert {item["input_type"] for item in questions} == {"time_window", "role_list"}

    start = datetime.now(UTC) + timedelta(days=2)
    end = start + timedelta(hours=2)
    second = client.post(
        "/intent/compile",
        headers=headers,
        json={
            "text": "想组一个项目团队",
            "clarification_round": 1,
            "answers": {
                "availability": f"{start.isoformat()}|{end.isoformat()}",
                "required_roles": "前端、产品",
            },
        },
    )
    assert second.status_code == 200, second.text
    result = second.json()["data"]
    assert result["needs_clarification"] is False
    assert result["questions"] == []
    assert set(result["card"]["required_roles"]) == {"frontend", "product"}
    assert len(result["card"]["available_windows"]) == 1
    assert result["card"]["field_sources"]["required_roles"] == "user_input"
    assert result["card"]["field_sources"]["available_windows"] == "user_input"


def _confirmed_gathering(client) -> str:
    for index in range(1, 5):
        headers = {"X-User-ID": f"u_demo_{index}"}
        card = client.post(
            "/intent/compile", headers=headers, json={"text": "一起完成 DDL，4人"}
        ).json()["data"]["card"]
        assert client.post(
            "/intent/publish", headers=headers, json={"card_id": card["id"]}
        ).status_code == 201
    run = client.post("/internal/matching/run", headers={"X-Admin-Token": "test-admin"})
    gathering_id = run.json()["data"]["gathering_ids"][0]
    for index in range(1, 5):
        assert client.post(
            f"/gatherings/{gathering_id}/confirm",
            headers={"X-User-ID": f"u_demo_{index}"},
            json={"confirmed": True},
        ).status_code == 200
    return gathering_id


def test_gathering_action_capability_is_server_authoritative(client):
    gathering_id = _confirmed_gathering(client)
    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.gathering_type = "DDL冲刺"
        gathering.location = "图书馆研讨室 15-401"
        gathering.start_at = datetime.now(UTC) + timedelta(days=4)
        gathering.end_at = gathering.start_at + timedelta(hours=2)
        db.commit()

    owner = {"X-User-ID": "u_demo_1"}
    capability = client.get(
        f"/gatherings/{gathering_id}/action-capability", headers=owner
    )
    assert capability.status_code == 200, capability.text
    data = capability.json()["data"]
    assert data["enabled"] is True
    assert data["action"] == "room.reserve_preview"
    assert data["params"]["kind"] == "15"
    assert data["params"]["room"] == "401"
    assert set(data["params"]["members"]) == {"u_demo_2", "u_demo_3", "u_demo_4"}
    preview = client.post(
        "/actions/preview",
        headers=owner,
        json={
            "action": data["action"],
            "params": data["params"],
            "gathering_id": gathering_id,
        },
    )
    assert preview.status_code == 200, preview.text

    non_owner = {"X-User-ID": "u_demo_2"}
    member_capability = client.get(
        f"/gatherings/{gathering_id}/action-capability", headers=non_owner
    )
    assert member_capability.status_code == 200
    member_data = member_capability.json()["data"]
    assert member_data["enabled"] is False
    assert member_data["action"] is None
    assert member_data["params"] == {}
    assert member_data["disabled_reason"] == "等待本局发起人处理行动预览"
    denied_preview = client.post(
        "/actions/preview",
        headers=non_owner,
        json={
            "action": data["action"],
            "params": data["params"],
            "gathering_id": gathering_id,
        },
    )
    assert denied_preview.status_code == 403


def test_unsupported_gathering_has_explicit_disabled_reason(client):
    gathering_id = _confirmed_gathering(client)
    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.id == gathering_id))
        assert gathering is not None
        gathering.gathering_type = "羽毛球"
        db.commit()
    response = client.get(
        f"/gatherings/{gathering_id}/action-capability",
        headers={"X-User-ID": "u_demo_1"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["enabled"] is False
    assert response.json()["data"]["disabled_reason"]


def test_intent_single_size_patch_validates_merged_card(client, auth_headers):
    card = client.post(
        "/intent/compile", headers=auth_headers, json={"text": "一起自习，3人"}
    ).json()["data"]["card"]
    too_large_min = client.patch(
        f"/intent/{card['id']}", headers=auth_headers, json={"min_size": 4}
    )
    assert too_large_min.status_code == 422
    too_small_target = client.patch(
        f"/intent/{card['id']}", headers=auth_headers, json={"target_size": 2}
    )
    assert too_small_target.status_code == 422


def test_intent_patch_preserves_datetime_types_and_json_windows(client, auth_headers):
    card = client.post(
        "/intent/compile", headers=auth_headers, json={"text": "一起自习，3人"}
    ).json()["data"]["card"]
    start = datetime.now(UTC) + timedelta(days=2)
    end = start + timedelta(hours=2)
    expires_at = end + timedelta(days=1)

    patched = client.patch(
        f"/intent/{card['id']}",
        headers=auth_headers,
        json={
            "available_windows": [
                {
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat(),
                    "stability": 0.9,
                }
            ],
            "expires_at": expires_at.isoformat(),
        },
    )

    assert patched.status_code == 200, patched.text
    result = patched.json()["data"]
    assert result["available_windows"][0]["start_at"].endswith("Z")
    assert result["available_windows"][0]["end_at"].endswith("Z")
    assert result["expires_at"].endswith("Z")
    published = client.post(
        "/intent/publish", headers=auth_headers, json={"card_id": card["id"]}
    )
    assert published.status_code == 201, published.text


def test_withdraw_uses_source_intent_and_rejects_later_state(client, auth_headers):
    cards = [
        client.post(
            "/intent/compile", headers=auth_headers, json={"text": "完全相同的自习目标"}
        ).json()["data"]["card"]
        for _ in range(2)
    ]
    published = [
        client.post(
            "/intent/publish", headers=auth_headers, json={"card_id": card["id"]}
        ).json()["data"]
        for card in cards
    ]
    removed = client.delete(f"/intent/{cards[0]['id']}", headers=auth_headers)
    assert removed.status_code == 200, removed.text
    first_response = client.get(
        f"/gatherings/{published[0]['gathering_id']}", headers=auth_headers
    )
    assert first_response.status_code == 404
    second = client.get(
        f"/gatherings/{published[1]['gathering_id']}", headers=auth_headers
    ).json()["data"]
    assert second["status"] == GatheringStatus.POOLING.value

    with SessionLocal() as db:
        first = db.get(Gathering, published[0]["gathering_id"])
        assert first is not None
        assert first.status == GatheringStatus.DISSOLVED.value
        gathering = db.get(Gathering, published[1]["gathering_id"])
        assert gathering is not None
        gathering.status = GatheringStatus.CONFIRMED.value
        card_model = __import__("onemore.db.models", fromlist=["IntentCard"]).IntentCard
        stored_card = db.get(card_model, cards[1]["id"])
        assert stored_card is not None
        stored_card.status = "Matched"
        db.commit()
    rejected = client.delete(f"/intent/{cards[1]['id']}", headers=auth_headers)
    assert rejected.status_code == 409


def test_pooling_member_can_submit_anonymous_gathering_safety_report(client, auth_headers):
    card = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={"text": "周六晚上一起自习，三个人"},
    ).json()["data"]["card"]
    published = client.post(
        "/intent/publish", headers=auth_headers, json={"card_id": card["id"]}
    )
    gathering_id = published.json()["data"]["gathering_id"]

    response = client.post(
        f"/gatherings/{gathering_id}/report",
        headers=auth_headers,
        json={"reason": "匿名阶段仍需平台核查本局描述", "block": False},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "submitted"
    invalid_block = client.post(
        f"/gatherings/{gathering_id}/report",
        headers=auth_headers,
        json={"reason": "未选择成员时不能执行拉黑", "block": True},
    )
    assert invalid_block.status_code == 422
    assert invalid_block.json()["error"]["code"] == "BLOCK_TARGET_REQUIRED"


def test_reschedule_notifies_other_members_with_calendar_refresh_payload(client):
    gathering_id = _confirmed_gathering(client)
    owner = {"X-User-ID": "u_demo_1"}
    detail = client.get(f"/gatherings/{gathering_id}", headers=owner).json()["data"]
    options = client.get(
        f"/gatherings/{gathering_id}/time-options", headers=owner
    ).json()["data"]
    assert options
    selected = options[0]
    response = client.post(
        f"/gatherings/{gathering_id}/reschedule",
        headers=owner,
        json={"start_at": selected["start_at"], "end_at": selected["end_at"]},
    )
    assert response.status_code == 200, response.text
    proposal = response.json()["data"]
    assert proposal["status"] == "open"
    assert proposal["accepted_count"] == 1
    assert proposal["required_count"] == 4
    assert proposal["my_vote"] == "accepted"
    current = client.get(
        f"/gatherings/{gathering_id}/reschedule", headers=owner
    ).json()["data"]
    assert current == proposal
    assert {
        "eligible_user_ids",
        "votes",
        "proposed_by",
        "participants",
    }.isdisjoint(current)
    unchanged = client.get(
        f"/gatherings/{gathering_id}", headers=owner
    ).json()["data"]
    assert unchanged["start_at"] == detail["start_at"]
    competing = client.post(
        f"/gatherings/{gathering_id}/reschedule",
        headers={"X-User-ID": "u_demo_2"},
        json={"start_at": selected["start_at"], "end_at": selected["end_at"]},
    )
    assert competing.status_code == 409
    assert competing.json()["error"]["code"] == "RESCHEDULE_VOTE_IN_PROGRESS"

    for index in (2, 3, 4):
        voted = client.post(
            f"/gatherings/{gathering_id}/reschedule/{proposal['proposal_id']}/vote",
            headers={"X-User-ID": f"u_demo_{index}"},
            json={"accepted": True},
        )
        assert voted.status_code == 200, voted.text
    assert voted.json()["data"]["status"] == "accepted"
    assert voted.json()["data"]["accepted_count"] == 4
    peer_notifications = client.get(
        "/notifications", headers={"X-User-ID": "u_demo_2"}
    ).json()["data"]
    event = next(item for item in peer_notifications if item["type"] == "gathering_rescheduled")
    assert event["payload"]["gathering_id"] == gathering_id
    assert event["payload"]["deep_link"].endswith(f"/{gathering_id}/space")
    assert event["payload"]["calendar_event"] == {
        "title": detail["title"],
        "start_at": selected["start_at"],
        "end_at": selected["end_at"],
        "location": detail["location"],
    }
    assert {"member_count", "participants", "reported_user_id"}.isdisjoint(
        event["payload"]["calendar_event"]
    )
    updated = client.get(
        f"/gatherings/{gathering_id}", headers=owner
    ).json()["data"]
    assert updated["start_at"] == selected["start_at"]
    assert updated["status"] == GatheringStatus.TENTATIVE.value


def test_reschedule_rejection_keeps_original_time_and_is_anonymous(client):
    gathering_id = _confirmed_gathering(client)
    owner = {"X-User-ID": "u_demo_1"}
    detail = client.get(f"/gatherings/{gathering_id}", headers=owner).json()["data"]
    selected = client.get(
        f"/gatherings/{gathering_id}/time-options", headers=owner
    ).json()["data"][0]
    proposal = client.post(
        f"/gatherings/{gathering_id}/reschedule",
        headers=owner,
        json={"start_at": selected["start_at"], "end_at": selected["end_at"]},
    ).json()["data"]
    rejected = client.post(
        f"/gatherings/{gathering_id}/reschedule/{proposal['proposal_id']}/vote",
        headers={"X-User-ID": "u_demo_2"},
        json={"accepted": False},
    )
    assert rejected.status_code == 200, rejected.text
    view = rejected.json()["data"]
    assert view["status"] == "rejected"
    assert view["my_vote"] == "declined"
    assert {"user_id", "voter", "proposed_by"}.isdisjoint(view)
    after = client.get(f"/gatherings/{gathering_id}", headers=owner).json()["data"]
    assert after["start_at"] == detail["start_at"]
    retry = client.post(
        f"/gatherings/{gathering_id}/reschedule/{proposal['proposal_id']}/vote",
        headers={"X-User-ID": "u_demo_2"},
        json={"accepted": False},
    )
    assert retry.status_code == 200
