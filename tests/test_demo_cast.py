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

    assert len(pooling) >= 8
    assert {item.title for item in pooling} >= {
        "周六英东羽毛球",
        "数模组队差建模",
        "数模组队差编程",
        "数模组队差两人",
        "数模组队差论文",
        "数模组队差代码",
        "数模组队招两人",
        "数模组队差建模手",
        "数模组队从零招人",
        "数模组队珠海差写作",
        "传设海报赶工",
        "商赛差调研",
        "逸夫讲座结伴",
        "东校夜场羽毛球",
        "黑客松差设计",
        "英语角试水",
        "生科报告互盯",
        "校博看展",
        "南校夜跑三公里",
        "东校篮球半场",
        "珠海咖啡店赶作业",
        "学一晚饭搭子",
        "周末桌游局",
    }

    assert any(item.title == "英东周三羽毛球" for item in completed)
    assert any(item.title == "智能应用开发大赛筹备" for item in completed)
    assert badminton.target_size - badminton_count == 1
    assert math_team.target_size - math_count == 1

    relations = client.get("/relations", headers={"X-User-ID": LIN}).json()["data"]
    assert relations
    taste = client.get("/profile/taste/me", headers={"X-User-ID": LIN}).json()["data"]
    assert taste["primary_tag"]["label"] == "探索型 Builder"


def test_campus_events_use_chinese_types_and_club_catalog(client):
    events = client.get("/events").json()["data"]
    types = {item["type"] for item in events}
    titles = {item["title"] for item in events}
    assert "teachin" not in types
    assert "seminar" not in types
    assert {"宣讲", "讲座", "社团", "招新"} <= types
    assert "互联网校招宣讲" in titles
    assert "街舞社周五夜练" in titles
    assert "志愿者协会招新" in titles


def test_open_gatherings_use_shanghai_daytime_hours():
    from zoneinfo import ZoneInfo

    from onemore.core.time import ensure_utc

    shanghai = ZoneInfo("Asia/Shanghai")
    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(Gathering).where(
                    Gathering.title.in_(
                        ("黑客松差设计", "校博看展", "东校夜场羽毛球", "传设海报赶工")
                    )
                )
            )
        )
    by_title = {item.title: item for item in rows}
    hackathon = ensure_utc(by_title["黑客松差设计"].start_at).astimezone(shanghai)
    museum = ensure_utc(by_title["校博看展"].start_at).astimezone(shanghai)
    night = ensure_utc(by_title["东校夜场羽毛球"].start_at).astimezone(shanghai)
    poster = ensure_utc(by_title["传设海报赶工"].start_at).astimezone(shanghai)
    assert hackathon.hour == 14
    assert museum.hour == 15
    assert night.hour == 20
    assert poster.hour == 19
    for item in rows:
        hour = ensure_utc(item.start_at).astimezone(shanghai).hour
        assert 10 <= hour <= 21, (item.title, hour)
