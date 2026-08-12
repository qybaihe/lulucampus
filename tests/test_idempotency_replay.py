from __future__ import annotations

import asyncio
import json
from contextlib import suppress

from sqlalchemy import func, select
from starlette.requests import Request
from starlette.responses import JSONResponse

from onemore.core.database import SessionLocal
from onemore.core.idempotency import IdempotencyCoordinator
from onemore.db.models import IdempotencyRecord, SecurityEvent


def _headers(key: str) -> dict[str, str]:
    return {"X-User-ID": "u_demo_1", "Idempotency-Key": key}


def test_publish_and_chat_replay_same_success_after_lost_response(client):
    card = client.post(
        "/intent/compile",
        headers={"X-User-ID": "u_demo_1"},
        json={"text": "周六一起自习，3人"},
    ).json()["data"]["card"]
    body = {"card_id": card["id"]}
    first = client.post("/intent/publish", headers=_headers("publish-lost-1"), json=body)
    replay = client.post("/intent/publish", headers=_headers("publish-lost-1"), json=body)
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert replay.headers["X-Idempotency-Replayed"] == "true"
    recovered = client.get(
        f"/intent/{card['id']}/publication", headers={"X-User-ID": "u_demo_1"}
    )
    assert recovered.status_code == 200
    assert recovered.json()["data"] == first.json()["data"]

    channel_id = next(
        item["channel_id"]
        for item in client.get("/relations", headers={"X-User-ID": "u_demo_1"}).json()[
            "data"
        ]
        if item["channel_id"]
    )
    message_body = {"content": "只发送一次", "content_type": "text"}
    sent = client.post(
        f"/channels/{channel_id}/messages",
        headers=_headers("message-lost-1"),
        json=message_body,
    )
    sent_replay = client.post(
        f"/channels/{channel_id}/messages",
        headers=_headers("message-lost-1"),
        json=message_body,
    )
    assert sent.status_code == sent_replay.status_code == 201
    assert sent.json()["data"]["id"] == sent_replay.json()["data"]["id"]
    messages = client.get(
        f"/channels/{channel_id}/messages", headers={"X-User-ID": "u_demo_1"}
    ).json()["data"]
    assert sum(item.get("content") == "只发送一次" for item in messages) == 1


def test_recur_and_organizer_create_are_replayed_once(client, admin_headers):
    mine = client.get("/gatherings/mine", headers={"X-User-ID": "u_demo_1"}).json()["data"]
    completed_id = next(item["id"] for item in mine if item["status"] == "Completed")
    body = {"keep_user_ids": None}
    first = client.post(
        f"/gatherings/{completed_id}/recur",
        headers=_headers("recur-lost-0001"),
        json=body,
    )
    replay = client.post(
        f"/gatherings/{completed_id}/recur",
        headers=_headers("recur-lost-0001"),
        json=body,
    )
    assert first.status_code == replay.status_code == 201
    assert first.json()["data"]["id"] == replay.json()["data"]["id"]

    assert client.post(
        "/internal/trust/u_demo_1/organizer-verification",
        headers=admin_headers,
        json={"verified": True},
    ).status_code == 200
    template = {
        "title": "幂等工作坊模板",
        "goal": "只创建一次",
        "gathering_type": "workshop",
        "location": "创新空间",
        "campus": "珠海校区",
        "min_size": 3,
        "target_size": 12,
        "duration_minutes": 90,
        "required_roles": [],
        "recurrence_rule": None,
    }
    created = client.post(
        "/organizer/templates", headers=_headers("template-lost-1"), json=template
    )
    created_replay = client.post(
        "/organizer/templates", headers=_headers("template-lost-1"), json=template
    )
    assert created.status_code == created_replay.status_code == 201
    assert created.json()["data"]["id"] == created_replay.json()["data"]["id"]


def test_reusing_key_with_different_body_is_rejected(client):
    first = client.post(
        "/intent/compile",
        headers=_headers("compile-conflict-1"),
        json={"text": "第一次意图"},
    )
    assert first.status_code == 200
    conflict = client.post(
        "/intent/compile",
        headers=_headers("compile-conflict-1"),
        json={"text": "不同的第二次意图"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_new_operation_occurrences_do_not_replay_stale_grant_or_join(client):
    base = {"X-User-ID": "u_demo_1"}
    for index, granted in enumerate((True, False, True)):
        response = client.post(
            "/auth/grants",
            headers={**base, "Idempotency-Key": f"grant-occurrence-{index}"},
            json={"scope": "timetable", "granted": granted},
        )
        assert response.status_code == 200
        assert response.json()["data"]["granted"] is granted
    grants = client.get("/auth/me", headers=base).json()["data"]["grants"]
    assert next(item for item in grants if item["scope"] == "timetable")["granted"] is True

    card = client.post(
        "/intent/compile", headers=base, json={"text": "一起自习，4人"}
    ).json()["data"]["card"]
    gathering_id = client.post(
        "/intent/publish", headers=base, json={"card_id": card["id"]}
    ).json()["data"]["gathering_id"]
    second = {"X-User-ID": "u_demo_2"}
    assert client.post(
        f"/gatherings/{gathering_id}/join",
        headers={**second, "Idempotency-Key": "join-occurrence-1"},
        json={},
    ).status_code == 200
    assert client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={**second, "Idempotency-Key": "leave-occurrence-1"},
        json={},
    ).status_code == 200
    joined_again = client.post(
        f"/gatherings/{gathering_id}/join",
        headers={**second, "Idempotency-Key": "join-occurrence-2"},
        json={},
    )
    assert joined_again.status_code == 200
    assert joined_again.json()["data"]["my_confirmation"] == "pending"


def test_commit_then_cancel_is_marked_unknown_and_never_executes_twice():
    coordinator = IdempotencyCoordinator()
    executions = 0

    def request() -> Request:
        body = b'{"operation":"commit-before-cancel"}'
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        value = Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/test/commit-cancel",
                "raw_path": b"/test/commit-cancel",
                "query_string": b"",
                "headers": [
                    (b"x-user-id", b"u_demo_1"),
                    (b"idempotency-key", b"commit-cancel-key"),
                    (b"content-type", b"application/json"),
                ],
                "client": ("127.0.0.1", 1),
                "server": ("test", 80),
            },
            receive,
        )
        value.state.request_id = "commit-cancel-request"
        return value

    async def scenario() -> None:
        nonlocal executions

        async def commit_then_cancel(_request):
            nonlocal executions
            executions += 1
            with SessionLocal() as db:
                db.add(
                    SecurityEvent(
                        user_id="u_demo_1",
                        event_type="idempotency_commit_cancel_probe",
                        details={"execution": executions},
                    )
                )
                db.commit()
            raise asyncio.CancelledError

        with suppress(asyncio.CancelledError):
            await coordinator.handle(request(), commit_then_cancel)

        async def must_not_run(_request):
            nonlocal executions
            executions += 1
            return JSONResponse({"data": {"unexpected": True}, "meta": {}})

        replay = await coordinator.handle(request(), must_not_run)
        assert replay.status_code == 409
        assert json.loads(replay.body)["error"]["code"] == "IDEMPOTENCY_RESULT_UNKNOWN"

    asyncio.run(scenario())
    assert executions == 1
    with SessionLocal() as db:
        record = db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.idempotency_key == "commit-cancel-key"
            )
        )
        assert record is not None
        assert record.response_status == -1
        count = db.scalar(
            select(func.count(SecurityEvent.id)).where(
                SecurityEvent.event_type == "idempotency_commit_cancel_probe"
            )
        )
        assert count == 1
