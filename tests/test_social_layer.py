"""社交感强化层：缺口卡、破冰包、搭子档案、信任叙事、回忆录、成局卡。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Gathering,
    GatheringMember,
    GatheringStatus,
    IntentCard,
    IntentStatus,
    Relation,
    SharedExperience,
)


def _seed_gathering(
    status: str,
    member_ids: list[str],
    *,
    mood_note: str | None = None,
    roles: dict[str, str] | None = None,
    mode: str = "similar",
    completed_at: datetime | None = None,
    official_metadata: dict | None = None,
    start_offset: timedelta = timedelta(days=2),
) -> str:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        intent = None
        if mood_note is not None:
            intent = IntentCard(
                user_id=member_ids[0],
                status=IntentStatus.POOLING.value,
                gathering_type="羽毛球",
                mode=mode,
                goal="打两小时羽毛球",
                mood_note=mood_note,
                expires_at=now + timedelta(days=1),
            )
            db.add(intent)
            db.flush()
        gathering = Gathering(
            source_intent_id=intent.id if intent else None,
            owner_user_id=member_ids[0],
            gathering_type="羽毛球",
            mode=mode,
            title="周六羽毛球局",
            goal="打两小时羽毛球",
            status=status,
            min_size=2,
            target_size=4,
            required_trust_level="T0",
            campus="珠海校区",
            identity_disclosure="after_confirmed",
            start_at=now + start_offset,
            end_at=now + start_offset + timedelta(hours=2),
            location="珠海校区综合馆",
            expires_at=now + timedelta(days=1),
            completed_at=completed_at,
            official_metadata=official_metadata or {},
        )
        db.add(gathering)
        db.flush()
        for member_id in member_ids:
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=member_id,
                    role=(roles or {}).get(member_id),
                    confirmation_status="confirmed",
                    completion_confirmed=completed_at is not None,
                )
            )
        db.commit()
        return gathering.id


def test_mood_note_flows_from_compile_to_gathering_detail(client, auth_headers):
    compiled = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={"text": "周六下午想打羽毛球，缺两个人", "mood_note": "考完试想出出汗"},
    )
    assert compiled.status_code == 200, compiled.text
    card = compiled.json()["data"]["card"]
    assert card["mood_note"] == "考完试想出出汗"

    published = client.post(
        "/intent/publish", headers=auth_headers, json={"card_id": card["id"]}
    )
    assert published.status_code == 201, published.text
    gathering_id = published.json()["data"]["gathering_id"]

    detail = client.get(f"/gatherings/{gathering_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["mood_note"] == "考完试想出出汗"


def test_gap_share_card_exposes_gap_and_anonymous_landing_page(client, auth_headers):
    gathering_id = _seed_gathering(
        GatheringStatus.POOLING.value,
        ["u_demo_1", "u_demo_2", "u_demo_3"],
        mood_note="就差一个了，来吗",
    )
    share = client.post(f"/gatherings/{gathering_id}/share", headers=auth_headers)
    assert share.status_code == 201, share.text
    data = share.json()["data"]
    assert data["missing_count"] == 1
    assert data["target_size"] == 4
    assert data["mood_note"] == "就差一个了，来吗"
    assert data["start_at"] is not None

    token = data["share_token"]
    resolved = client.get(f"/shares/g/{token}")
    assert resolved.status_code == 200
    assert resolved.json()["data"]["missing_count"] == 1

    page = client.get(f"/g/{token}")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    body = page.text
    assert "还差 1 人" in body
    for display_name in ("林予安", "周衡", "陈可薇", "梁景行", "苏晚宁", "何屿"):
        assert display_name not in body


def test_icebreaker_requires_membership_and_confirmed_state(client, auth_headers):
    pooling_id = _seed_gathering(GatheringStatus.POOLING.value, ["u_demo_1", "u_demo_2"])
    not_ready = client.get(f"/gatherings/{pooling_id}/icebreaker", headers=auth_headers)
    assert not_ready.status_code == 409
    assert not_ready.json()["error"]["code"] == "ICEBREAKER_NOT_READY"

    confirmed_id = _seed_gathering(
        GatheringStatus.CONFIRMED.value,
        ["u_demo_1", "u_demo_2", "u_demo_4"],
        roles={"u_demo_1": "后端", "u_demo_2": "前端", "u_demo_4": "产品"},
        mode="complementary",
    )
    outsider = client.get(
        f"/gatherings/{confirmed_id}/icebreaker", headers={"X-User-ID": "u_demo_3"}
    )
    assert outsider.status_code == 403

    response = client.get(f"/gatherings/{confirmed_id}/icebreaker", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["headline"]
    kinds = {fact["kind"] for fact in data["facts"]}
    # u_demo_1 与 u_demo_2 同上 CS2002-01，这是现成的社交燃料。
    assert "common_course" in kinds
    assert "role_complement" in kinds
    assert 1 <= len(data["first_lines"]) <= 3
    assert data["next_steps"]["location"] == "珠海校区综合馆"
    assert any("时间" in item for item in data["next_steps"]["checklist"])


def test_relation_profile_translates_facts_into_warm_narrative(client, auth_headers):
    now = datetime.now(UTC)
    first = _seed_gathering(
        GatheringStatus.COMPLETED.value,
        ["u_demo_1", "u_demo_2"],
        completed_at=now - timedelta(days=14),
        start_offset=timedelta(days=-14, hours=-2),
    )
    recurred = _seed_gathering(
        GatheringStatus.COMPLETED.value,
        ["u_demo_1", "u_demo_2"],
        completed_at=now - timedelta(days=7),
        official_metadata={"created_via": "recurrence_choice", "parent_gathering_id": first},
        start_offset=timedelta(days=-7, hours=-2),
    )
    third = _seed_gathering(
        GatheringStatus.COMPLETED.value,
        ["u_demo_1", "u_demo_2"],
        completed_at=now - timedelta(days=1),
        official_metadata={"created_via": "recurrence_choice", "parent_gathering_id": recurred},
        start_offset=timedelta(days=-1, hours=-2),
    )
    with SessionLocal() as db:
        from sqlalchemy import select

        relation = db.scalar(
            select(Relation).where(
                Relation.participant_a_id == "u_demo_1",
                Relation.participant_b_id == "u_demo_2",
            )
        )
        if relation is None:
            relation = Relation(
                participant_a_id="u_demo_1",
                participant_b_id="u_demo_2",
                created_from_gathering_id=first,
            )
            db.add(relation)
            db.flush()
        relation.status = "active"
        for gathering_id, days in ((first, 14), (recurred, 7), (third, 1)):
            db.add(
                SharedExperience(
                    relation_id=relation.id,
                    gathering_id=gathering_id,
                    participants=["u_demo_1", "u_demo_2"],
                    gathering_type="羽毛球",
                    occurred_at=now - timedelta(days=days),
                    outcome="completed",
                    common_grounds=["同上《数据结构与算法》"],
                )
            )
        db.commit()
        relation_id = relation.id

    detail = client.get(f"/relations/{relation_id}", headers=auth_headers)
    assert detail.status_code == 200, detail.text
    data = detail.json()["data"]
    # 种子数据里这对搭子已有 3 段经历，本测试新增 3 段（其中 2 段复局）。
    times = data["times_together"]
    assert times >= 3
    assert len(data["timeline"]) == times
    assert data["recur_count"] >= 2
    assert data["is_fixed_partner"] is True
    assert data["partner_title"] == "固定搭子"
    steps = (1, 3, 5, 10, 20)
    expected_reached = max((step for step in steps if step <= times), default=0)
    expected_next = next((step for step in steps if step > times), None)
    assert data["milestone"]["reached"] == expected_reached
    assert data["milestone"]["next"] == expected_next
    if expected_next is not None:
        assert data["milestone"]["remaining"] == expected_next - times
    newest = data["timeline"][0]
    assert newest["via_recurrence"] is True
    assert newest["duration_minutes"] == 120
    assert newest["location"] == "珠海校区综合馆"
    assert "next_window" in data
    assert "active_goal" in data

    listing = client.get("/relations", headers=auth_headers)
    assert listing.status_code == 200
    listed = next(item for item in listing.json()["data"] if item["id"] == relation_id)
    assert listed["partner_title"] == "固定搭子"


def test_trust_progress_returns_unlock_narrative(client, auth_headers):
    response = client.get("/trust/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["level_narrative"]
    assert data["current_benefits"]
    assert data["level_guide"]
    assert len(data["level_guide"]) == 5
    assert data["level_guide"][0]["level"] == "T0"
    assert "benefits" in data["level_guide"][0]
    if data["next_level"] in {"T2", "T3"}:
        assert data["next_level_progress"], data
        metric = data["next_level_progress"][0]
        assert {"key", "label", "current", "required", "unit"} <= set(metric)
        assert data["conditions"], data
        assert data["next_level_name"]
        assert data["next_benefits"]
        assert 0 <= data["overall_progress"] <= 1
        condition = data["conditions"][0]
        assert {"key", "label", "met"} <= set(condition)
    # 技术能力键仍在 payload 中供调试，但不应是客户端主展示路径的唯一内容
    assert data["unlocks"]


def test_semester_recap_aggregates_facts_with_anonymous_share_text(client, auth_headers):
    now = datetime.now(UTC)
    for days in (3, 10):
        _seed_gathering(
            GatheringStatus.COMPLETED.value,
            ["u_demo_1", "u_demo_2"],
            completed_at=now - timedelta(days=days),
            start_offset=timedelta(days=-days, hours=-2),
        )
    response = client.get("/me/recap", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["gatherings_completed"] >= 2
    assert data["partners_met"] >= 1
    assert data["total_hours"] >= 4
    assert data["top_partner"]["times_together"] >= 2
    assert "还差一个" in data["share_text"]
    assert data["highlights"]


def test_channel_opens_with_system_gathering_card(client, auth_headers):
    gathering_id = _seed_gathering(
        GatheringStatus.CONFIRMED.value,
        ["u_demo_1", "u_demo_2"],
        roles={"u_demo_1": "组织", "u_demo_2": "记录"},
    )
    with SessionLocal() as db:
        from onemore.modules.collab.service import open_gathering_channel

        channel = open_gathering_channel(db, gathering_id)
        db.commit()
        channel_id = channel.id

    messages = client.get(f"/channels/{channel_id}/messages", headers=auth_headers)
    assert messages.status_code == 200, messages.text
    data = messages.json()["data"]
    assert data, "channel should open with the system gathering card"
    first = data[0]
    assert first["sender_type"] == "system"
    assert "成局卡" in first["content"]
    assert "地点：珠海校区综合馆" in first["content"]
    assert "分工：组织 / 记录" in first["content"]
    assert data[1]["sender_type"] == "azou"


def test_today_timeline_datetimes_are_timezone_aware(client, auth_headers):
    """回归：iOS ISO8601 解码拒绝 naive 时间，时间线所有条目必须带时区。"""
    gathering_id = _seed_gathering(
        GatheringStatus.CONFIRMED.value,
        ["u_demo_1", "u_demo_2"],
        start_offset=timedelta(minutes=30),
    )

    response = client.get("/today/summary", headers=auth_headers)
    assert response.status_code == 200, response.text
    timeline = response.json()["data"]["timeline"]
    entries = [item for item in timeline if item.get("id") == gathering_id]
    assert entries, "seeded gathering should appear on today's timeline"
    for item in timeline:
        for key in ("start_at", "end_at"):
            raw = item.get(key)
            if raw is None:
                continue
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            assert parsed.tzinfo is not None, f"{item['kind']}.{key} 缺少时区: {raw}"


def test_assignment_due_dates_are_timezone_aware(client, auth_headers):
    """回归：作业列表与详情的 due_at 也必须带时区（iOS 同一解码器）。"""
    response = client.get("/assignments", params={"status": "unfinished"}, headers=auth_headers)
    assert response.status_code == 200, response.text
    items = response.json()["data"]
    for item in items:
        parsed = datetime.fromisoformat(item["due_at"].replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, f"assignments.due_at 缺少时区: {item['due_at']}"
    if items:
        detail = client.get(f"/assignments/{items[0]['id']}", headers=auth_headers)
        assert detail.status_code == 200, detail.text
        raw = detail.json()["data"]["due_at"]
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, f"assignment_detail.due_at 缺少时区: {raw}"
