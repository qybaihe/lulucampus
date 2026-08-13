from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Assignment,
    Course,
    Enrollment,
    Gathering,
    GatheringMember,
    GatheringStatus,
)
from onemore.modules.notify.service import (
    push,
    schedule_campus_reminders,
    schedule_gathering_reminders,
)


def test_campus_reminders_land_in_filterable_inbox(client, auth_headers):
    now = datetime.now(UTC)
    class_start = now + timedelta(minutes=30)
    due_at = now + timedelta(hours=2)
    with SessionLocal() as db:
        course = db.scalar(select(Course).limit(1))
        assert course is not None
        db.add(
            Enrollment(
                user_id="u_demo_1",
                course_id=course.id,
                class_code="remind-lab",
                term="2026-fall",
                status="current",
                meeting_windows=[
                    {
                        "week": 1,
                        "start_at": class_start.isoformat(),
                        "end_at": (class_start + timedelta(hours=2)).isoformat(),
                        "location": "东校园",
                    }
                ],
            )
        )
        db.add(
            Assignment(
                user_id="u_demo_1",
                course_id=course.id,
                title="提醒作业",
                due_at=due_at,
                status="unfinished",
            )
        )
        db.commit()
        sent = schedule_campus_reminders(db)
        assert sent >= 2

    items = client.get("/notifications", headers=auth_headers).json()["data"]
    schedule = next(item for item in items if item["type"] == "schedule_reminder")
    assignment = next(item for item in items if item["type"] == "assignment_reminder")
    assert schedule["category"] == "schedule_reminders"
    assert schedule["title"] == "课表快到了"
    assert "上课" in schedule["payload"]["summary"]
    assert schedule["payload"]["deep_link"] == "onemore://screen/B3"
    assert assignment["category"] == "schedule_reminders"
    assert "截止" in assignment["payload"]["summary"]
    assert assignment["payload"]["deep_link"] == "onemore://screen/B4"

    filtered = client.get(
        "/notifications",
        headers=auth_headers,
        params={"category": "schedule_reminders"},
    ).json()["data"]
    assert filtered
    assert all(item["category"] == "schedule_reminders" for item in filtered)

    chat_only = client.get(
        "/notifications",
        headers=auth_headers,
        params={"category": "chat_messages"},
    ).json()["data"]
    assert all(item["category"] == "chat_messages" for item in chat_only)


def test_gathering_reminder_includes_human_summary(client, auth_headers):
    start_at = datetime.now(UTC) + timedelta(hours=2)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习搭子",
            mode="similar",
            title="图书馆冲刺",
            goal="把提醒写进人话",
            status=GatheringStatus.EXECUTED.value,
            min_size=2,
            target_size=2,
            start_at=start_at,
            end_at=start_at + timedelta(hours=2),
        )
        db.add(gathering)
        db.flush()
        db.add(GatheringMember(gathering_id=gathering.id, user_id="u_demo_1"))
        db.commit()
        assert schedule_gathering_reminders(db) >= 1

    items = client.get("/notifications", headers=auth_headers).json()["data"]
    reminder = next(item for item in items if item["type"] == "gathering_reminder")
    assert reminder["category"] == "gathering_updates"
    assert reminder["payload"]["summary"] == "「图书馆冲刺」还有 2 小时"


def test_shared_goal_peer_support_is_an_allowed_inbox_type(client, auth_headers):
    with SessionLocal() as db:
        push(
            db,
            "u_demo_1",
            "shared_goal_peer_support",
            {
                "relation_id": "rel-fixture",
                "summary": "共同目标有一位成员暂时低于本期节奏，可以一起确认下一次行动。",
                "deep_link": "onemore://goal/rel-fixture",
            },
        )
        db.commit()

    items = client.get("/notifications", headers=auth_headers).json()["data"]
    item = next(row for row in items if row["type"] == "shared_goal_peer_support")
    assert item["category"] == "gathering_updates"
    assert item["title"] == "共同目标"


def test_disabled_schedule_category_still_keeps_inbox_history(client, auth_headers):
    assert (
        client.patch(
            "/me/notification-preferences",
            headers=auth_headers,
            json={"categories": {"schedule_reminders": False}},
        ).status_code
        == 200
    )
    due_at = datetime.now(UTC) + timedelta(hours=2)
    with SessionLocal() as db:
        course = db.scalar(select(Course).limit(1))
        assert course is not None
        db.add(
            Assignment(
                user_id="u_demo_1",
                course_id=course.id,
                title="关闭分类后仍可见",
                due_at=due_at,
                status="unfinished",
            )
        )
        db.commit()
        assert schedule_campus_reminders(db) >= 1

    items = client.get("/notifications", headers=auth_headers).json()["data"]
    assignment = next(item for item in items if item["type"] == "assignment_reminder")
    assert assignment["payload"]["push_delivery_suppressed"] is True
    assert assignment["payload"]["summary"] == "「关闭分类后仍可见」还有 2 小时截止"

