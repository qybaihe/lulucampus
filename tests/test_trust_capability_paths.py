from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import (
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    IntentCard,
    Notification,
    TrustProfile,
    User,
    UserBlock,
)


def _set_level(user_id: str, level: str) -> None:
    with SessionLocal() as db:
        profile = db.get(TrustProfile, user_id)
        assert profile is not None
        profile.level = level
        profile.organizer_verified = level == "T4"
        db.commit()


def test_t2_self_initiation_is_distinct_from_t1_intent_pool(client, auth_headers):
    payload = {
        "title": "直接发起羽毛球局",
        "goal": "周五一起练双打",
        "gathering_type": "羽毛球",
        "campus": "珠海校区",
        "location": "体育馆 2 号场",
        "min_size": 3,
        "target_size": 4,
    }
    _set_level("u_demo_1", "T1")
    denied = client.post("/gatherings/initiate", headers=auth_headers, json=payload)
    assert denied.status_code == 403
    assert denied.json()["error"]["details"]["capability"] == "initiate_gathering"

    _set_level("u_demo_1", "T2")
    created = client.post("/gatherings/initiate", headers=auth_headers, json=payload)
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["status"] == "Pooling"
    # 招募期暴露池内纯计数（无身份）：发起人为第 1 位成员
    assert data["member_count"] == 1
    with SessionLocal() as db:
        item = db.get(Gathering, data["id"])
        assert item is not None
        assert item.source_intent_id is None
        assert item.owner_user_id == "u_demo_1"
        assert item.official_metadata["created_via"] == "self_initiation"


def test_self_initiation_duo_threshold_and_cross_college_require_all_members_t2(
    client, auth_headers
):
    _set_level("u_demo_1", "T2")
    duo = client.post(
        "/gatherings/initiate",
        headers=auth_headers,
        json={
            "title": "最低两人成局",
            "goal": "测试两人门槛",
            "gathering_type": "自习",
            "min_size": 2,
            "target_size": 3,
        },
    )
    assert duo.status_code == 201
    assert duo.json()["data"]["required_trust_level"] == "T2"
    _set_level("u_demo_2", "T1")
    with SessionLocal() as db:
        candidate = db.get(User, "u_demo_2")
        assert candidate is not None
        candidate.minimum_group_size = 2
        db.commit()
    denied_duo = client.post(
        f"/gatherings/{duo.json()['data']['id']}/join",
        headers={"X-User-ID": "u_demo_2"},
        json={},
    )
    assert denied_duo.status_code == 403
    denied_error = denied_duo.json()["error"]
    assert denied_error["code"] == "TRUST_LEVEL_REQUIRED"
    assert denied_error["details"] == {
        "required_level": "T2",
        "capability": "duo_gathering",
    }

    with SessionLocal() as db:
        owner = db.get(User, "u_demo_1")
        candidate = db.get(User, "u_demo_2")
        assert owner is not None and candidate is not None
        owner.college = "软件学院"
        candidate.college = "医学院"
        db.commit()
    cross = client.post(
        "/gatherings/initiate",
        headers=auth_headers,
        json={
            "title": "跨院系项目",
            "goal": "跨专业共创",
            "gathering_type": "项目",
            "min_size": 3,
            "target_size": 4,
            "cross_college": True,
        },
    )
    assert cross.status_code == 201
    assert cross.json()["data"]["required_trust_level"] == "T2"
    denied_cross = client.post(
        f"/gatherings/{cross.json()['data']['id']}/join",
        headers={"X-User-ID": "u_demo_2"},
        json={},
    )
    assert denied_cross.status_code == 403


def test_t3_recurring_fixed_series_enforces_gate_and_server_schedule(client, auth_headers):
    first_start = datetime.now(UTC) + timedelta(days=10)
    with SessionLocal() as db:
        original = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习",
            mode="similar",
            title="每周论文冲刺",
            goal="固定完成论文进度",
            status=GatheringStatus.COMPLETED.value,
            min_size=3,
            target_size=4,
            required_trust_level="T1",
            campus="珠海校区",
            start_at=datetime.now(UTC) - timedelta(days=1, hours=2),
            end_at=datetime.now(UTC) - timedelta(days=1),
            completed_at=datetime.now(UTC) - timedelta(days=1),
        )
        db.add(original)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
            db.add(
                GatheringMember(
                    gathering_id=original.id,
                    user_id=user_id,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                    completion_confirmed=True,
                )
            )
        db.commit()
        original_id = original.id

    _set_level("u_demo_1", "T2")
    body = {
        "first_start_at": first_start.isoformat(),
        "occurrences": 3,
        "interval_weeks": 2,
        "duration_minutes": 90,
    }
    denied = client.post(
        f"/gatherings/{original_id}/recurring", headers=auth_headers, json=body
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["details"]["capability"] == "recurring_gathering"

    _set_level("u_demo_1", "T3")
    created = client.post(
        f"/gatherings/{original_id}/recurring", headers=auth_headers, json=body
    )
    assert created.status_code == 201, created.text
    rows = created.json()["data"]
    assert len(rows) == 3
    assert all(row["status"] == "Tentative" for row in rows)
    starts = [datetime.fromisoformat(row["start_at"].replace("Z", "+00:00")) for row in rows]
    assert starts[1] - starts[0] == timedelta(weeks=2)
    assert starts[2] - starts[1] == timedelta(weeks=2)
    with SessionLocal() as db:
        series = [db.get(Gathering, row["id"]) for row in rows]
        assert len({item.official_metadata["recurrence"]["series_id"] for item in series if item}) == 1
        original = db.get(Gathering, original_id)
        assert original is not None
        assert original.status == GatheringStatus.COMPLETED.value

    # A fixed series is the owner's private choice; it must not consume the
    # original Completed state or prevent a peer from quietly choosing later.
    peer_finished = client.post(
        f"/gatherings/{original_id}/recur/finish",
        headers={"X-User-ID": "u_demo_2"},
    )
    assert peer_finished.status_code == 200, peer_finished.text
    assert peer_finished.json()["data"]["decision"] == "ended"
    peer_view = client.get(
        f"/gatherings/{original_id}", headers={"X-User-ID": "u_demo_2"}
    ).json()["data"]
    assert peer_view["status"] == GatheringStatus.COMPLETED.value
    assert peer_view["my_recurrence_decision"]["decision"] == "ended"
    duplicate = client.post(
        f"/gatherings/{original_id}/recurring",
        headers={**auth_headers, "Idempotency-Key": "fresh-series-duplicate-key"},
        json=body,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "RECURRENCE_ALREADY_DECIDED"


def test_t3_recurring_rechecks_member_privacy_and_pairwise_blocks(client, auth_headers):
    first_start = datetime.now(UTC) + timedelta(days=15)
    with SessionLocal() as db:
        original = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习",
            mode="similar",
            title="不应复制的固定局",
            goal="安全重验",
            status=GatheringStatus.COMPLETED.value,
            min_size=3,
            target_size=4,
            required_trust_level="T1",
            campus="珠海校区",
            completed_at=datetime.now(UTC),
        )
        db.add(original)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
            db.add(
                GatheringMember(
                    gathering_id=original.id,
                    user_id=user_id,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                    completion_confirmed=True,
                )
            )
        db.commit()
        original_id = original.id
        blocked_user = db.get(User, "u_demo_2")
        assert blocked_user is not None
        blocked_user.social_enabled = False
        db.commit()

    _set_level("u_demo_1", "T3")
    response = client.post(
        f"/gatherings/{original_id}/recurring",
        headers=auth_headers,
        json={
            "first_start_at": first_start.isoformat(),
            "occurrences": 2,
            "duration_minutes": 60,
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RECURRING_MEMBER_PRIVACY_CHANGED"
    with SessionLocal() as db:
        assert not list(db.scalars(select(Gathering).where(Gathering.title == "不应复制的固定局", Gathering.id != original_id)))
        member = db.get(User, "u_demo_2")
        assert member is not None
        member.social_enabled = True
        db.add(UserBlock(blocker_id="u_demo_2", blocked_id="u_demo_1"))
        db.commit()

    blocked = client.post(
        f"/gatherings/{original_id}/recurring",
        headers=auth_headers,
        json={
            "first_start_at": first_start.isoformat(),
            "occurrences": 2,
            "duration_minutes": 60,
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "RECURRING_MEMBER_BLOCKED"


def test_t3_backfill_fast_lane_has_real_priority_and_never_reveals_history(client):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="羽毛球",
            mode="similar",
            title="临时补位",
            goal="补齐三人练习",
            status=GatheringStatus.TENTATIVE.value,
            min_size=3,
            target_size=4,
            required_trust_level="T1",
            campus="珠海校区",
            start_at=now + timedelta(hours=4),
            end_at=now + timedelta(hours=6),
            expires_at=now + timedelta(hours=3),
        )
        db.add(gathering)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user_id,
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                )
            )
        for user_id in ("u_demo_3", "u_demo_4"):
            db.add(
                IntentCard(
                    user_id=user_id,
                    status="Pooling",
                    gathering_type="羽毛球",
                    goal="寻找羽毛球补位",
                    campus="珠海校区",
                    expires_at=now + timedelta(days=1),
                )
            )
        db.commit()
        gathering_id = gathering.id

    _set_level("u_demo_3", "T2")
    _set_level("u_demo_4", "T3")
    left = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_3"},
        json={"reason": "提前离开"},
    )
    assert left.status_code == 200, left.text
    assert left.json()["data"]["status"] == "Pooling"

    ordinary = client.get(
        f"/gatherings/{gathering_id}/backfill",
        headers={"X-User-ID": "u_demo_3"},
    ).json()["data"]
    assert ordinary["fast_lane_active"] is True
    assert ordinary["viewer_fast_lane_eligible"] is False
    assert ordinary["history_visible"] is False
    denied = client.post(
        f"/gatherings/{gathering_id}/backfill/claim",
        headers={"X-User-ID": "u_demo_3"},
        json={},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["details"]["capability"] == "backfill_fast_lane"
    bypass = client.post(
        f"/gatherings/{gathering_id}/join",
        headers={"X-User-ID": "u_demo_3"},
        json={},
    )
    assert bypass.status_code == 409
    assert bypass.json()["error"]["code"] == "BACKFILL_CLAIM_REQUIRED"

    fast = client.get(
        f"/gatherings/{gathering_id}/backfill",
        headers={"X-User-ID": "u_demo_4"},
    ).json()["data"]
    assert fast["viewer_fast_lane_eligible"] is True
    assert fast["claim_available_at"] < fast["fast_lane_until"]
    claimed = client.post(
        f"/gatherings/{gathering_id}/backfill/claim",
        headers={"X-User-ID": "u_demo_4"},
        json={},
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["data"]["status"] == "Tentative"

    with SessionLocal() as db:
        notices = list(
            db.scalars(
                select(Notification).where(
                    Notification.type == "backfill_invitation",
                    Notification.user_id.in_(["u_demo_3", "u_demo_4"]),
                )
            )
        )
        by_user = {item.user_id: item.payload for item in notices}
        assert by_user["u_demo_3"]["fast_lane"] is False
        assert by_user["u_demo_4"]["fast_lane"] is True
        assert all(item.payload["history_visible"] is False for item in notices)


def test_executed_departure_reopens_backfill_and_claim_consumes_intent_atomically(client):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习",
            mode="similar",
            title="已预约待开始补位",
            goal="补回退出成员",
            status=GatheringStatus.EXECUTED.value,
            min_size=3,
            target_size=4,
            required_trust_level="T1",
            campus="珠海校区",
            start_at=now + timedelta(hours=5),
            end_at=now + timedelta(hours=7),
            expires_at=now + timedelta(hours=4),
        )
        db.add(gathering)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user_id,
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                )
            )
        candidate = IntentCard(
            user_id="u_demo_4",
            status="Pooling",
            gathering_type="自习",
            goal="愿意补位",
            campus="珠海校区",
            expires_at=now + timedelta(days=1),
        )
        db.add(candidate)
        db.commit()
        gathering_id = gathering.id
        candidate_id = candidate.id

    _set_level("u_demo_4", "T3")
    left = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_3"},
        json={"reason": "开始前退出"},
    )
    assert left.status_code == 200
    assert left.json()["data"]["status"] == "Pooling"
    panel = client.get(
        f"/gatherings/{gathering_id}/backfill",
        headers={"X-User-ID": "u_demo_4"},
    )
    assert panel.status_code == 200
    assert panel.json()["data"]["open"] is True

    with SessionLocal() as db:
        item = db.get(Gathering, gathering_id)
        assert item is not None
        metadata = dict(item.official_metadata)
        backfill = dict(metadata["backfill"])
        backfill["fast_lane_until"] = (now - timedelta(minutes=1)).isoformat()
        metadata["backfill"] = backfill
        item.official_metadata = metadata
        db.commit()

    generic = client.post(
        f"/gatherings/{gathering_id}/join",
        headers={"X-User-ID": "u_demo_4"},
        json={"joined_via": "backfill"},
    )
    assert generic.status_code == 409
    assert generic.json()["error"]["code"] == "BACKFILL_CLAIM_REQUIRED"
    with SessionLocal() as db:
        assert db.get(IntentCard, candidate_id).status == "Pooling"

    claimed = client.post(
        f"/gatherings/{gathering_id}/backfill/claim",
        headers={"X-User-ID": "u_demo_4"},
        json={},
    )
    assert claimed.status_code == 200, claimed.text
    with SessionLocal() as db:
        assert db.get(IntentCard, candidate_id).status == "Matched"
        member = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == "u_demo_4",
            )
        )
        assert member is not None
        assert member.joined_via == "backfill"


def test_active_departure_extends_replacement_window_until_event_end(client):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="羽毛球",
            mode="similar",
            title="进行中补位",
            goal="活动结束前补回成员",
            status=GatheringStatus.ACTIVE.value,
            min_size=3,
            target_size=4,
            required_trust_level="T1",
            campus="珠海校区",
            start_at=now - timedelta(minutes=20),
            end_at=now + timedelta(hours=1),
            expires_at=now - timedelta(minutes=30),
        )
        db.add(gathering)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user_id,
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                )
            )
        db.add(
            IntentCard(
                user_id="u_demo_4",
                status="Pooling",
                gathering_type="羽毛球",
                goal="进行中也愿意补位",
                campus="珠海校区",
                expires_at=now + timedelta(days=1),
            )
        )
        db.commit()
        gathering_id = gathering.id
    _set_level("u_demo_4", "T3")
    left = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_3"},
        json={"reason": "活动中提前离开"},
    )
    assert left.status_code == 200
    assert left.json()["data"]["status"] == "Pooling"
    panel = client.get(
        f"/gatherings/{gathering_id}/backfill",
        headers={"X-User-ID": "u_demo_4"},
    )
    assert panel.status_code == 200
    assert panel.json()["data"]["open"] is True
    claimed = client.post(
        f"/gatherings/{gathering_id}/backfill/claim",
        headers={"X-User-ID": "u_demo_4"},
        json={},
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["data"]["status"] == "Tentative"


def test_backfill_failure_exposes_typed_fallback_and_reconfirms_reduced_plan(client):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="项目组会",
            mode="similar",
            title="四人项目组会",
            goal="完成方案评审",
            status=GatheringStatus.TENTATIVE.value,
            min_size=4,
            target_size=4,
            required_trust_level="T1",
            campus="珠海校区",
            location="教学楼研讨室",
            start_at=now + timedelta(hours=5),
            end_at=now + timedelta(hours=7),
            expires_at=now + timedelta(hours=4),
        )
        db.add(gathering)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3", "u_demo_4"):
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user_id,
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                )
            )
        db.commit()
        gathering_id = gathering.id

    left = client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_4"},
        json={"reason": "提前退出"},
    )
    assert left.status_code == 200
    panel = client.get(
        f"/gatherings/{gathering_id}/backfill",
        headers={"X-User-ID": "u_demo_1"},
    )
    assert panel.status_code == 200
    options = {item["key"]: item for item in panel.json()["data"]["fallback_options"]}
    assert options["reduce_to_three"]["min_size"] == 3
    assert options["move_online"]["location"] == "线上"
    denied = client.post(
        f"/gatherings/{gathering_id}/backfill/fallback",
        headers={"X-User-ID": "u_demo_4"},
        json={"option_key": "reduce_to_three"},
    )
    assert denied.status_code == 403

    applied = client.post(
        f"/gatherings/{gathering_id}/backfill/fallback",
        headers={"X-User-ID": "u_demo_1"},
        json={"option_key": "reduce_to_three"},
    )
    assert applied.status_code == 200, applied.text
    data = applied.json()["data"]
    assert data["status"] == "Tentative"
    assert data["target_size"] == 3
    assert data["confirmed_count"] == 0
    with SessionLocal() as db:
        item = db.get(Gathering, gathering_id)
        assert item is not None
        assert "backfill" not in item.official_metadata
        assert item.official_metadata["backfill_fallback"]["key"] == "reduce_to_three"


def test_normal_pooling_never_exposes_backfill_fallback_actions(client):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="项目组会",
            mode="similar",
            title="普通招募",
            goal="等待首次成局",
            status=GatheringStatus.POOLING.value,
            min_size=3,
            target_size=4,
            required_trust_level="T1",
            start_at=now + timedelta(hours=4),
            end_at=now + timedelta(hours=6),
            expires_at=now + timedelta(hours=3),
        )
        db.add(gathering)
        db.flush()
        db.add(
            GatheringMember(
                gathering_id=gathering.id,
                user_id="u_demo_1",
                joined_via="owner",
            )
        )
        db.commit()
        gathering_id = gathering.id

    panel = client.get(
        f"/gatherings/{gathering_id}/backfill",
        headers={"X-User-ID": "u_demo_1"},
    )
    assert panel.status_code == 200
    assert panel.json()["data"]["open"] is False
    assert panel.json()["data"]["fallback_options"] == []
    rejected = client.post(
        f"/gatherings/{gathering_id}/backfill/fallback",
        headers={"X-User-ID": "u_demo_1"},
        json={"option_key": "move_online"},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "BACKFILL_NOT_OPEN"


def test_backfill_fallback_rechecks_blocks_atomically(client):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="项目组会",
            mode="similar",
            title="四人组会",
            goal="完成评审",
            status=GatheringStatus.TENTATIVE.value,
            min_size=4,
            target_size=4,
            required_trust_level="T1",
            start_at=now + timedelta(hours=4),
            end_at=now + timedelta(hours=6),
            expires_at=now + timedelta(hours=3),
        )
        db.add(gathering)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3", "u_demo_4"):
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user_id,
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                )
            )
        db.commit()
        gathering_id = gathering.id

    assert client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_4"},
        json={"reason": "提前退出"},
    ).status_code == 200
    with SessionLocal() as db:
        db.add(UserBlock(blocker_id="u_demo_2", blocked_id="u_demo_1"))
        db.commit()

    rejected = client.post(
        f"/gatherings/{gathering_id}/backfill/fallback",
        headers={"X-User-ID": "u_demo_1"},
        json={"option_key": "reduce_to_three"},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "BACKFILL_FALLBACK_MEMBER_BLOCKED"
    with SessionLocal() as db:
        item = db.get(Gathering, gathering_id)
        assert item is not None
        assert item.status == GatheringStatus.POOLING.value
        assert item.target_size == 4
        assert "backfill" in item.official_metadata
        assert "backfill_fallback" not in item.official_metadata
        confirmation_notices = list(
            db.scalars(
                select(Notification).where(
                    Notification.type == "confirmation_required",
                    Notification.payload["gathering_id"].as_string() == gathering_id,
                )
            )
        )
        assert confirmation_notices == []


def test_backfill_fallback_deadline_never_outlives_event_and_ended_join_fails(client):
    now = datetime.now(UTC)
    end_at = now + timedelta(hours=6)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="项目组会",
            mode="similar",
            title="线下转线上",
            goal="完成评审",
            status=GatheringStatus.TENTATIVE.value,
            min_size=4,
            target_size=4,
            required_trust_level="T1",
            location="教学楼研讨室",
            start_at=now + timedelta(hours=4),
            end_at=end_at,
            expires_at=now + timedelta(hours=3),
        )
        db.add(gathering)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3", "u_demo_4"):
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user_id,
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                    joined_via="owner" if user_id == "u_demo_1" else "intent",
                )
            )
        db.commit()
        gathering_id = gathering.id

    assert client.post(
        f"/gatherings/{gathering_id}/leave",
        headers={"X-User-ID": "u_demo_4"},
        json={"reason": "提前退出"},
    ).status_code == 200
    applied = client.post(
        f"/gatherings/{gathering_id}/backfill/fallback",
        headers={"X-User-ID": "u_demo_1"},
        json={"option_key": "move_online"},
    )
    assert applied.status_code == 200, applied.text
    with SessionLocal() as db:
        item = db.get(Gathering, gathering_id)
        assert item is not None and item.expires_at is not None
        assert item.expires_at <= item.start_at
        item.start_at = now - timedelta(hours=2)
        item.end_at = now - timedelta(hours=1)
        item.expires_at = now + timedelta(days=1)
        db.commit()

    rejected = client.post(
        f"/gatherings/{gathering_id}/join",
        headers={"X-User-ID": "u_demo_4"},
        json={},
    )
    assert rejected.status_code == 410
    assert rejected.json()["error"]["code"] == "GATHERING_EXPIRED"
