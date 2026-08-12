from __future__ import annotations

from sqlalchemy import func, select

from onemore.core.database import SessionLocal
from onemore.db.demo_cast import CAST_PASSWORD, CAST_USERS, LIN
from onemore.db.models import Gathering, GatheringMember, GatheringStatus, TasteProfile, User


def _member_count(db, gathering_id: str) -> int:
    return int(
        db.scalar(
            select(func.count(GatheringMember.id)).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
        or 0
    )


def test_cast_users_are_registered_like_real_accounts(client):
    roster = {item.id: item for item in CAST_USERS}
    with SessionLocal() as db:
        for spec in CAST_USERS:
            user = db.get(User, spec.id)
            assert user is not None
            assert user.display_name == spec.display_name
            assert user.college == spec.college
            assert user.campus == spec.campus
            assert user.grade_year == spec.grade_year
            assert user.gender_code == spec.gender_code
            assert user.social_enabled is True
            assert user.verified_at is not None
            assert user.phone == spec.phone
            assert db.get(TasteProfile, spec.id) is not None

    me = client.get("/auth/me", headers={"X-User-ID": LIN}).json()["data"]
    assert me["display_name"] == roster[LIN].display_name
    assert me["college"] == "软件工程学院"
    assert me["campus"] == "珠海校区"

    login = client.post(
        "/auth/login",
        json={"phone": roster[LIN].phone, "password": CAST_PASSWORD},
    )
    assert login.status_code == 200, login.text
    assert login.json()["data"]["user_id"] == LIN


def test_cast_has_history_and_open_gaps_for_real_users(client):
    with SessionLocal() as db:
        completed = list(
            db.scalars(select(Gathering).where(Gathering.status == GatheringStatus.COMPLETED.value))
        )
        pooling = list(
            db.scalars(select(Gathering).where(Gathering.status == GatheringStatus.POOLING.value))
        )
        badminton = next(item for item in pooling if item.title == "周六英东羽毛球")
        math_team = next(item for item in pooling if item.title == "数模组队差建模")
        badminton_count = _member_count(db, badminton.id)
        math_count = _member_count(db, math_team.id)

    assert any(item.title == "英东周三羽毛球" for item in completed)
    assert any(item.title == "智能应用开发大赛筹备" for item in completed)
    assert badminton.target_size - badminton_count == 1
    assert math_team.target_size - math_count == 1

    relations = client.get("/relations", headers={"X-User-ID": LIN}).json()["data"]
    assert relations
    taste = client.get("/profile/taste/me", headers={"X-User-ID": LIN}).json()["data"]
    assert taste["primary_tag"]["label"] == "探索型 Builder"
