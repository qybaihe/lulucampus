from __future__ import annotations

from onemore.core.database import SessionLocal
from onemore.db.models import CampusAction, ChannelParticipant, User
from onemore.hermes.campus_mcp import dispatch_tool, mint_tool_session
from onemore.modules.campus.peers import start_peer_chat, suggest_peers


def test_same_course_suggests_zhou_for_lin():
    with SessionLocal() as db:
        peers = suggest_peers(db, "u_demo_1", {"course_codes": ["CS2002"]})
    names = {item["display_name"] for item in peers}
    assert "周衡" in names
    zhou = next(item for item in peers if item["display_name"] == "周衡")
    assert zhou["overlap"] == "course"
    assert "机器学习" in zhou["reason"]
    assert "netid" not in zhou
    assert "user_id" in zhou


def test_question_infers_machine_learning_course():
    with SessionLocal() as db:
        peers = suggest_peers(db, "u_demo_1", {"question": "还有谁也选了机器学习？"})
    assert any(item["display_name"] == "周衡" and item["overlap"] == "course" for item in peers)


def test_gym_slot_overlap(client, auth_headers):
    with SessionLocal() as db:
        db.add(
            CampusAction(
                user_id="u_demo_2",
                action_name="gym.book_preview",
                params={
                    "venue_type": "羽毛球",
                    "date": "2026-08-20",
                    "start": "19:00",
                    "end": "21:00",
                    "venue": "南校园",
                },
                preview_snapshot={},
                snapshot_hash="peer-gym-hash",
                idempotency_key="peer-gym-key",
            )
        )
        db.commit()
        peers = suggest_peers(
            db,
            "u_demo_1",
            {"venue_type": "羽毛球", "date": "2026-08-20", "start": "19:00"},
        )
    assert any(item["display_name"] == "周衡" and item["overlap"] == "gym" for item in peers)


def test_social_opt_out_hides_peer():
    with SessionLocal() as db:
        zhou = db.get(User, "u_demo_2")
        assert zhou is not None
        zhou.social_enabled = False
        db.commit()
        peers = suggest_peers(db, "u_demo_1", {"course_codes": ["CS2002"]})
    assert all(item["display_name"] != "周衡" for item in peers)


def test_start_peer_chat_opens_channel(client, auth_headers):
    from sqlalchemy import select

    with SessionLocal() as db:
        user = db.get(User, "u_demo_1")
        opened = start_peer_chat(
            db, user, "u_demo_2", reason="也选了机器学习（CS2002）", overlap="course"
        )
    assert opened["channel_id"]
    assert opened["gathering_id"]
    with SessionLocal() as db:
        ids = set(
            db.scalars(
                select(ChannelParticipant.user_id).where(
                    ChannelParticipant.channel_id == opened["channel_id"]
                )
            )
        )
    assert ids == {"u_demo_1", "u_demo_2"}

    again = client.post(
        "/hermes/peers/start",
        headers=auth_headers,
        json={
            "peer_user_id": "u_demo_2",
            "reason": "也选了机器学习（CS2002）",
            "overlap": "course",
        },
    )
    assert again.status_code == 200, again.text
    assert again.json()["data"]["channel_id"] == opened["channel_id"]


def test_hermes_ask_find_basketball_partner_returns_peers(client, auth_headers):
    response = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={"text": "我想打篮球 帮我找找搭子"},
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["card_type"] == "peer_list"
    assert body["kind"] in {"result", "agent"}
    assert body.get("action") == "campus.peers"
    peers = body["data"]["peers"]
    assert peers
    gym = [item for item in peers if item.get("overlap") == "gym"]
    assert {"梁景行", "何屿"} <= {item["display_name"] for item in gym}


def test_hermes_ask_social_question_returns_peers(client, auth_headers):
    response = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={"text": "还有谁也选了机器学习？"},
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["card_type"] == "peer_list"
    peers = body["data"]["peers"]
    assert any(item["display_name"] == "周衡" for item in peers)
    assert "周衡" in (body["data"].get("message") or "")


def test_campus_peers_tool(client, auth_headers):
    with SessionLocal() as db:
        token = mint_tool_session(db, "u_demo_1", question="还有谁选了机器学习")
        result = dispatch_tool(
            "campus_peers",
            {"course_code": "CS2002", "question": "还有谁选了机器学习"},
            tool_session=token,
            db=db,
        )
    assert result["ok"] is True
    assert result["card_type"] == "peer_list"
    assert any(item["display_name"] == "周衡" for item in result["data"]["peers"])


def test_commit_still_forbidden_with_peers_tool():
    from onemore.core.errors import AppError
    from onemore.hermes.campus_mcp import CAMPUS_TOOLS, assert_tool_allowed, openai_tool_schemas

    names = {tool.name for tool in CAMPUS_TOOLS}
    assert "campus_peers" in names
    assert not any("commit" in name for name in names)
    schema_names = {item["function"]["name"] for item in openai_tool_schemas()}
    assert schema_names == names
    try:
        assert_tool_allowed("gym_book_commit")
        raise AssertionError("commit must stay forbidden")
    except AppError as exc:
        assert exc.code == "TOOL_FORBIDDEN"


def test_overlap_template_machine_learning_has_several_classmates():
    with SessionLocal() as db:
        peers = suggest_peers(db, "u_demo_1", {"course_codes": ["CS2002"]})
    names = {item["display_name"] for item in peers if item["overlap"] == "course"}
    assert {"周衡", "梁景行", "何屿"} <= names


def test_overlap_template_badminton_uses_seeded_slots():
    with SessionLocal() as db:
        peers = suggest_peers(db, "u_demo_1", {"question": "还有谁也约了羽毛球？"})
    gym_names = {item["display_name"] for item in peers if item["overlap"] == "gym"}
    assert len(gym_names) >= 3
    assert {"周衡", "何屿"} <= gym_names
    assert all("机器学习" not in (item["reason"] or "") for item in peers)


def test_overlap_template_basketball_tonight():
    with SessionLocal() as db:
        peers = suggest_peers(db, "u_demo_1", {"question": "今晚有谁也约了篮球？"})
    gym = [item for item in peers if item["overlap"] == "gym"]
    names = {item["display_name"] for item in gym}
    assert {"梁景行", "何屿"} <= names
    assert all("今晚同一时段也约了篮球" in (item["reason"] or "") for item in gym)


def test_hermes_ask_books_basketball_and_attaches_cast_peers(client, auth_headers):
    response = client.post(
        "/hermes/ask",
        headers=auth_headers,
        json={"text": "今晚想打篮球，帮我预约体育馆，看看有没有人也约了、兴趣相同的"},
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["kind"] == "action_preview"
    assert body["action"] == "gym.book_preview"
    params = body["data"]["params"]
    assert params["venue_type"] == "篮球"
    assert params["start"] == "19:00"
    assert params["end"] == "21:00"
    peers = body["data"]["peers"]
    names = {item["display_name"] for item in peers if item.get("overlap") == "gym"}
    assert {"梁景行", "何屿"} <= names
    message = body["data"].get("message") or ""
    assert "何屿" in message or "梁景行" in message
    assert "确认后才会真正下单" in message


def test_overlap_template_attaches_extra_user():
    from sqlalchemy import select

    from onemore.db.models import Course, Enrollment, new_id
    from onemore.db.peer_overlap import attach_user_to_overlap

    extra_id = new_id()
    with SessionLocal() as db:
        user = User(
            id=extra_id,
            netid_hash=f"overlap-extra-{extra_id[:8]}",
            display_name="测试搭子",
            account_status="active",
        )
        db.add(user)
        db.flush()
        attach_user_to_overlap(db, user)
        db.commit()
        codes = set(
            db.scalars(
                select(Course.code)
                .join(Enrollment, Enrollment.course_id == Course.id)
                .where(Enrollment.user_id == extra_id, Enrollment.status == "current")
            )
        )
        peers = suggest_peers(db, extra_id, {"course_codes": ["CS2002"], "venue_type": "羽毛球"})
    assert {"CS2002", "GE4101", "PE1204"} <= codes
    names = {item["display_name"] for item in peers}
    assert "林予安" in names
    assert "周衡" in names
