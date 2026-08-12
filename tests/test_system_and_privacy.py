from __future__ import annotations

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Enrollment,
    GatheringMember,
    GatheringTransition,
    Message,
    SharedExperience,
)
from onemore.hermes.catalog import CATALOG


def test_health_and_required_routes(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    paths = client.get("/openapi.json").json()["paths"]
    required = {
        "/auth/session",
        "/profile/me",
        "/schedule/timetable",
        "/intent/compile",
        "/gatherings/mine",
        "/trust/me",
        "/channels/{channel_id}/messages",
        "/relations",
        "/competitions",
        "/actions/preview",
        "/notifications",
    }
    assert required <= set(paths)


def test_forbidden_capabilities_are_structurally_absent(client):
    paths = client.get("/openapi.json").json()["paths"]
    forbidden_paths = {
        "/users/search",
        "/friends/request",
        "/relations/recommend",
        "/trust/{user_id}",
        "/career/job/apply",
        "/jwxt/leave/apply",
    }
    assert forbidden_paths.isdisjoint(paths)
    action_names = {action.value for action in CATALOG}
    forbidden_actions = {
        "leave.apply",
        "career.job_apply",
        "career.signup",
        "workstudy.apply",
        "course.select",
        "grade.fetch",
        "payment.submit",
    }
    assert action_names.isdisjoint(forbidden_actions)


def test_ethics_fields_do_not_exist_in_database_models():
    enrollment_columns = set(Enrollment.__table__.columns.keys())
    experience_columns = set(SharedExperience.__table__.columns.keys())
    message_columns = set(Message.__table__.columns.keys())
    assert {"grade", "score", "gpa"}.isdisjoint(enrollment_columns)
    assert {"rating", "impression", "tags", "note"}.isdisjoint(experience_columns)
    assert {"read", "read_at", "seen_at"}.isdisjoint(message_columns)


def test_pooling_view_hides_membership(client, auth_headers):
    compiled = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={"text": "周六想找三个人一起打羽毛球"},
    ).json()["data"]["card"]
    published = client.post(
        "/intent/publish",
        headers=auth_headers,
        json={"card_id": compiled["id"]},
    )
    assert published.status_code == 201
    gathering_id = published.json()["data"]["gathering_id"]
    owner_view = client.get(f"/gatherings/{gathering_id}", headers=auth_headers).json()["data"]
    stranger_view = client.get(
        f"/gatherings/{gathering_id}", headers={"X-User-ID": "u_demo_2"}
    ).json()["data"]
    for view in (owner_view, stranger_view):
        assert view["status"] == "Pooling"
        # 产品决策（2026-08-12）：招募期暴露池内纯计数（无身份），
        # confirmed_count / participants 仍隐藏。
        assert view["member_count"] == 1
        assert view["confirmed_count"] is None
        assert view["participants"] is None


def test_schedule_intersection_has_no_identity_fields(client, admin_headers):
    response = client.post(
        "/internal/schedule/intersections",
        headers=admin_headers,
        json={"user_ids": ["u_demo_1", "u_demo_2", "u_demo_3"]},
    )
    assert response.status_code == 200
    for window in response.json()["data"]:
        assert "user_id" not in window
        assert "user_ids" not in window
        assert set(window) == {
            "start_at",
            "end_at",
            "feasible_count",
            "stability",
            "campus_reachable",
        }


def test_declined_member_is_not_retained_or_attributed(client, admin_headers):
    for index in range(1, 4):
        headers = {"X-User-ID": f"u_demo_{index}"}
        card = client.post(
            "/intent/compile",
            headers=headers,
            json={"text": "周六晚上三个人一起打羽毛球"},
        ).json()["data"]["card"]
        client.post("/intent/publish", headers=headers, json={"card_id": card["id"]})
    formed = client.post("/internal/matching/run", headers=admin_headers).json()["data"]
    gathering_id = formed["gathering_ids"][0]
    declined = client.post(
        f"/gatherings/{gathering_id}/confirm",
        headers={"X-User-ID": "u_demo_2"},
        json={"confirmed": False},
    )
    assert declined.status_code == 200
    with SessionLocal() as db:
        membership = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == "u_demo_2",
            )
        )
        transition = db.scalar(
            select(GatheringTransition)
            .where(GatheringTransition.gathering_id == gathering_id)
            .order_by(GatheringTransition.occurred_at.desc())
        )
        assert membership is None
        assert transition is not None and transition.actor_user_id is None
