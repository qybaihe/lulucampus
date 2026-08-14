from __future__ import annotations

from onemore.db.demo_cast import CUMCM_GD_2026, CUMCM_RECRUITING_TITLES, LIN
from onemore.db.models import Gathering, GatheringMember, GatheringStatus


def _overlap_gathering(
    db,
    *,
    owner_id: str,
    member_ids: list[str],
    title: str,
    gathering_type: str,
    status: str,
    start_at,
    end_at,
    official_metadata: dict | None = None,
) -> Gathering:
    gathering = Gathering(
        owner_user_id=owner_id,
        gathering_type=gathering_type,
        mode="similar",
        title=title,
        goal=title,
        status=status,
        min_size=3,
        target_size=4,
        required_trust_level="T0",
        campus="南校园",
        identity_disclosure="after_confirmed",
        start_at=start_at,
        end_at=end_at,
        location="南校园英东体育中心",
        official_metadata=official_metadata or {},
    )
    db.add(gathering)
    db.flush()
    for member_id in member_ids:
        db.add(
            GatheringMember(
                gathering_id=gathering.id,
                user_id=member_id,
                joined_via="owner" if member_id == owner_id else "open",
                confirmation_status="confirmed",
            )
        )
    return gathering


def _math_modeling(client) -> dict:
    return next(
        item
        for item in client.get("/competitions").json()["data"]
        if item["name"] == CUMCM_GD_2026
    )


def test_math_modeling_lists_recruiting_teams(client):
    competition = _math_modeling(client)
    teams = client.get(f"/competitions/{competition['id']}/teams").json()["data"]
    titles = {item["title"] for item in teams}
    assert titles == set(CUMCM_RECRUITING_TITLES)
    by_title = {item["title"]: item for item in teams}

    modeling = by_title["数模组队差建模"]
    assert modeling["member_count"] == 2
    assert modeling["min_size"] == 2
    assert modeling["target_size"] == 3
    assert modeling["missing_count"] == 1
    assert modeling["missing_roles"] == ["modeling"]
    assert modeling["required_roles"] == ["modeling"]
    assert modeling["filled_roles"] == ["编程", "写作"]
    assert "差一个建模" in (modeling.get("goal") or "")

    programming = by_title["数模组队差编程"]
    assert programming["member_count"] == 2
    assert programming["missing_count"] == 1
    assert programming["missing_roles"] == ["programming"]
    assert programming["filled_roles"] == ["建模", "写作"]
    assert "按角色互补" in (programming.get("roster_highlights") or [])
    assert any(
        item in {"高手带队", "有人带过队"}
        for item in (programming.get("roster_highlights") or [])
    )

    two_gaps = by_title["数模组队差两人"]
    assert two_gaps["member_count"] == 1
    assert two_gaps["missing_count"] == 2
    assert two_gaps["missing_roles"] == ["modeling", "paper_writing"]
    assert two_gaps["filled_roles"] == ["编程"]

    paper = by_title["数模组队差论文"]
    assert paper["member_count"] == 2
    assert paper["missing_roles"] == ["paper_writing"]
    assert paper["filled_roles"] == ["编程", "建模"]

    solo = by_title["数模组队招两人"]
    assert solo["member_count"] == 1
    assert solo["missing_count"] == 2
    assert solo["missing_roles"] == ["programming", "paper_writing"]
    assert solo["campus"] == "南校园"

    from_scratch = by_title["数模组队从零招人"]
    assert from_scratch["member_count"] == 1
    assert from_scratch["missing_roles"] == ["modeling", "programming"]
    assert from_scratch["filled_roles"] == ["写作"]

    zhuhai = by_title["数模组队珠海差写作"]
    assert zhuhai["campus"] == "珠海校区"
    assert zhuhai["member_count"] == 2
    assert zhuhai["missing_roles"] == ["paper_writing"]


def test_competition_team_stays_listed_after_work_session_ends(client):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.models import Gathering
    from onemore.modules.gathering.service import dissolve_expired, is_expired

    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.title == "数模组队差论文"))
        assert gathering is not None
        gathering.end_at = datetime.now(UTC) - timedelta(hours=1)
        gathering.expires_at = datetime.now(UTC) + timedelta(days=7)
        db.commit()
        db.refresh(gathering)
        assert is_expired(gathering) is False
        dissolve_expired(db)

    competition = _math_modeling(client)
    titles = {
        item["title"]
        for item in client.get(f"/competitions/{competition['id']}/teams").json()["data"]
    }
    assert "数模组队差论文" in titles


def test_competition_team_detail_is_anonymous_and_scoped(client):
    competition = _math_modeling(client)
    teams = client.get(f"/competitions/{competition['id']}/teams").json()["data"]
    team = next(item for item in teams if item["title"] == "数模组队差建模")
    detail = client.get(
        f"/competitions/{competition['id']}/teams/{team['id']}"
    ).json()["data"]
    assert detail["id"] == team["id"]
    assert detail["missing_count"] == 1
    assert "user_id" not in detail
    assert "owner_user_id" not in detail
    assert "members" not in detail

    missing = client.get(f"/competitions/{competition['id']}/teams/not-a-team")
    assert missing.status_code == 404

    other = next(
        item
        for item in client.get("/competitions").json()["data"]
        if item["id"] != competition["id"]
    )
    crossed = client.get(f"/competitions/{other['id']}/teams/{team['id']}")
    assert crossed.status_code == 404


def test_pooling_gathering_shows_chinese_roles_and_anonymous_roster(client, auth_headers):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.models import Gathering

    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.title == "数模组队差编程"))
        assert gathering is not None
        gathering_id = gathering.id

    data = client.get(f"/gatherings/{gathering_id}", headers=auth_headers).json()["data"]
    assert data["looking_for"] == ["编程"]
    assert "programming" not in data["looking_for"]
    assert data["filled_roles"] == ["建模", "写作"]
    assert "按角色互补" in data["roster_highlights"]
    assert any(item in {"高手带队", "有人带过队"} for item in data["roster_highlights"])
    assert data["participants"] is None
    assert "陈可薇" not in str(data)
    assert data["member_count"] == 2
    assert data["target_size"] == 3


def test_join_not_blocked_by_existing_member_group_size(client):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.demo_cast import CHEN, LIN
    from onemore.db.models import Gathering, User

    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.title == "数模组队差编程"))
        assert gathering is not None
        owner = db.get(User, CHEN)
        assert owner is not None
        owner.minimum_group_size = 4
        db.commit()
        gathering_id = gathering.id

    joined = client.post(
        f"/gatherings/{gathering_id}/join",
        headers={"X-User-ID": LIN},
        json={"role": "programming"},
    )
    assert joined.status_code == 200, joined.text
    data = joined.json()["data"]
    assert data["member_count"] == 3
    assert data["status"] == "Confirmed"
    assert data["channel_id"]
    assert "GATHERING_PRIVACY_CHANGED" not in joined.text


def test_join_competition_team_ignores_calendar_timeslot(client):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.modules.gathering.service import _time_conflict

    with SessionLocal() as db:
        team = db.scalar(select(Gathering).where(Gathering.title == "数模组队差编程"))
        assert team is not None
        assert team.start_at is not None and team.end_at is not None
        team_id = team.id
        _overlap_gathering(
            db,
            owner_id=LIN,
            member_ids=[LIN],
            title="同时段羽毛球",
            gathering_type="羽毛球",
            status=GatheringStatus.CONFIRMED.value,
            start_at=team.start_at,
            end_at=team.end_at,
        )
        assert _time_conflict(db, LIN, team) is False
        db.commit()

    joined = client.post(
        f"/gatherings/{team_id}/join",
        headers={"X-User-ID": LIN},
        json={"role": "programming"},
    )
    assert joined.status_code == 200, joined.text
    data = joined.json()["data"]
    assert data["member_count"] == 3
    assert data["status"] == "Confirmed"
    assert data["channel_id"]


def test_regular_join_still_blocked_by_same_slot(client):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.demo_cast import ZHOU
    from onemore.modules.gathering.service import _time_conflict

    with SessionLocal() as db:
        team = db.scalar(select(Gathering).where(Gathering.title == "数模组队差编程"))
        assert team is not None
        start_at, end_at = team.start_at, team.end_at
        _overlap_gathering(
            db,
            owner_id=LIN,
            member_ids=[LIN],
            title="已确认羽毛球",
            gathering_type="羽毛球",
            status=GatheringStatus.CONFIRMED.value,
            start_at=start_at,
            end_at=end_at,
        )
        pooling = _overlap_gathering(
            db,
            owner_id=ZHOU,
            member_ids=[ZHOU],
            title="想加入的同时段羽毛球",
            gathering_type="羽毛球",
            status=GatheringStatus.POOLING.value,
            start_at=start_at,
            end_at=end_at,
        )
        pooling.expires_at = end_at
        pooling_id = pooling.id
        assert _time_conflict(db, LIN, pooling) is True
        db.commit()

    blocked = client.post(
        f"/gatherings/{pooling_id}/join",
        headers={"X-User-ID": LIN},
        json={},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "TIME_CONFLICT"


def test_confirmed_competition_does_not_block_same_slot_join(client):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.demo_cast import ZHOU
    from onemore.modules.gathering.service import _time_conflict

    with SessionLocal() as db:
        team = db.scalar(select(Gathering).where(Gathering.title == "数模组队差建模"))
        assert team is not None
        team.status = GatheringStatus.CONFIRMED.value
        pooling = _overlap_gathering(
            db,
            owner_id=ZHOU,
            member_ids=[ZHOU],
            title="比赛同时段羽毛球",
            gathering_type="羽毛球",
            status=GatheringStatus.POOLING.value,
            start_at=team.start_at,
            end_at=team.end_at,
        )
        pooling.expires_at = team.end_at
        pooling_id = pooling.id
        assert LIN in {
            member.user_id
            for member in db.scalars(
                select(GatheringMember).where(
                    GatheringMember.gathering_id == team.id,
                    GatheringMember.left_at.is_(None),
                )
            )
        }
        assert _time_conflict(db, LIN, pooling) is False
        db.commit()

    joined = client.post(
        f"/gatherings/{pooling_id}/join",
        headers={"X-User-ID": LIN},
        json={},
    )
    assert joined.status_code == 200, joined.text


def test_join_two_person_competition_team_seals_and_opens_channel(client, auth_headers):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.models import Gathering

    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.title == "数模组队差编程"))
        assert gathering is not None
        assert gathering.min_size == 2
        gathering_id = gathering.id

    joined = client.post(f"/gatherings/{gathering_id}/join", headers=auth_headers, json={})
    assert joined.status_code == 200, joined.text
    data = joined.json()["data"]
    assert data["status"] == "Confirmed"
    assert data["member_count"] == 3
    assert data["my_confirmation"] == "confirmed"
    assert data["channel_id"]
    assert data["looking_for"] == []
    assert data["participants"]


def test_join_one_person_competition_team_seals_at_min_size(client, auth_headers):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.models import Gathering

    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.title == "数模组队差两人"))
        assert gathering is not None
        gathering_id = gathering.id

    joined = client.post(f"/gatherings/{gathering_id}/join", headers=auth_headers, json={})
    assert joined.status_code == 200, joined.text
    data = joined.json()["data"]
    assert data["status"] == "Confirmed"
    assert data["member_count"] == 2
    assert data["my_confirmation"] == "confirmed"
    assert data["channel_id"]
    assert data["looking_for"] == []


def test_join_competition_team_ignores_t1_teammate_cross_college(client, auth_headers):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.demo_cast import SU
    from onemore.db.models import Gathering, TrustProfile, User

    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.title == "数模组队差建模手"))
        assert gathering is not None
        su = db.get(User, SU)
        trust = db.get(TrustProfile, SU)
        assert su is not None and trust is not None
        assert su.college == "外国语学院"
        assert trust.level == "T1"
        gathering_id = gathering.id

    joined = client.post(
        f"/gatherings/{gathering_id}/join",
        headers=auth_headers,
        json={"role": "modeling"},
    )
    assert joined.status_code == 200, joined.text
    data = joined.json()["data"]
    assert data["status"] == "Confirmed"
    assert data["member_count"] == 3
    assert data["channel_id"]
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.models import Gathering, GatheringMember

    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.title == "数模组队差建模"))
        assert gathering is not None
        gathering_id = gathering.id
        member = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == LIN,
            )
        )
        assert member is not None
        member.joined_via = "open"
        db.commit()

    joined = client.post(f"/gatherings/{gathering_id}/join", headers=auth_headers, json={})
    assert joined.status_code == 200, joined.text
    data = joined.json()["data"]
    assert data["status"] == "Confirmed"
    assert data["member_count"] == 2
    assert data["channel_id"]
    assert data["looking_for"] == []


def test_regular_join_stays_tentative_until_confirm(client):
    from sqlalchemy import select

    from onemore.core.database import SessionLocal
    from onemore.db.demo_cast import ZHOU
    from onemore.db.models import Gathering

    with SessionLocal() as db:
        gathering = db.scalar(select(Gathering).where(Gathering.title == "周六英东羽毛球"))
        assert gathering is not None
        gathering_id = gathering.id

    joined = client.post(
        f"/gatherings/{gathering_id}/join",
        headers={"X-User-ID": ZHOU},
        json={},
    )
    assert joined.status_code == 200, joined.text
    data = joined.json()["data"]
    assert data["status"] == "Tentative"
    assert data["channel_id"] is None
    assert data["member_count"] == 4

