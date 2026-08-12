from __future__ import annotations

import pytest

from onemore.core.database import SessionLocal
from onemore.core.errors import AppError
from onemore.hermes.agent_gateway import map_sidecar_payload
from onemore.hermes.campus_mcp import (
    CAMPUS_TOOLS,
    assert_tool_allowed,
    dispatch_tool,
    mint_tool_session,
    openai_tool_schemas,
)


def test_campus_tools_never_expose_commit():
    names = {tool.name for tool in CAMPUS_TOOLS}
    assert not any("commit" in name for name in names)
    schemas = openai_tool_schemas()
    schema_names = {item["function"]["name"] for item in schemas}
    assert schema_names == names
    with pytest.raises(AppError) as exc:
        assert_tool_allowed("gym_book_commit")
    assert exc.value.code == "TOOL_FORBIDDEN"
    with pytest.raises(AppError) as exc:
        assert_tool_allowed("room.reserve_commit")
    assert exc.value.code == "TOOL_FORBIDDEN"


def test_dispatch_preview_does_not_commit(client, auth_headers):
    with SessionLocal() as db:
        token = mint_tool_session(db, "u_demo_1", question="订场")
        result = dispatch_tool(
            "gym_book_preview",
            {
                "venue_type": "羽毛球",
                "date": "2026-08-20",
                "start": "19:00",
                "end": "21:00",
                "venue": "南校园",
            },
            tool_session=token,
            db=db,
        )
    assert result["ok"] is True
    assert result["kind"] == "action_preview"
    assert result["requires_preview"] is True
    assert result["action"] == "gym.book_preview"
    assert result["data"]["next"] == "/actions/preview"
    assert result["data"]["params"]["venue_type"] == "羽毛球"


def test_dispatch_timetable_today_fake(client, auth_headers):
    with SessionLocal() as db:
        token = mint_tool_session(db, "u_demo_1", question="今天有什么课")
        result = dispatch_tool("timetable_today", {}, tool_session=token, db=db)
    assert result["ok"] is True
    assert result["card_type"] == "course_list"
    assert result["action"] == "timetable.today"


def test_mcp_http_rejects_commit(client):
    with SessionLocal() as db:
        token = mint_tool_session(db, "u_demo_1")
    response = client.post(
        "/internal/campus-mcp/tools/call",
        json={"name": "room_reserve_commit", "arguments": {}, "tool_session": token},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TOOL_FORBIDDEN"


def test_mcp_http_requires_session(client):
    response = client.post(
        "/internal/campus-mcp/tools/call",
        json={"name": "timetable_today", "arguments": {}, "tool_session": "short"},
    )
    assert response.status_code == 422


def test_map_sidecar_payload_keeps_preview_and_trace():
    mapped = map_sidecar_payload(
        {
            "choices": [{"message": {"content": "已生成预览，请确认后再预约。"}}],
            "tool_trace": [{"name": "gym_book_preview", "ok": True, "summary": "已生成预览"}],
            "structured": {
                "ok": True,
                "kind": "action_preview",
                "action": "gym.book_preview",
                "card_type": "action_preview",
                "requires_preview": True,
                "data": {"params": {"venue_type": "羽毛球"}, "next": "/actions/preview"},
            },
        },
        "南校园羽毛球",
    )
    assert mapped["kind"] == "action_preview"
    assert mapped["requires_preview"] is True
    assert mapped["data"]["params"]["venue_type"] == "羽毛球"
    assert mapped["tool_trace"][0]["name"] == "gym_book_preview"
    assert "已生成预览" in mapped["data"]["message"]


def test_hermes_ask_still_falls_back_to_rules(client, auth_headers):
    response = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={"text": "今天有什么课？"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["card_type"] == "course_list"
    assert body["kind"] in {"result", "agent"}
