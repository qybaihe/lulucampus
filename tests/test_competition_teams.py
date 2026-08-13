from __future__ import annotations

from onemore.db.demo_cast import CUMCM_GD_2026


def _math_modeling(client) -> dict:
    return next(
        item
        for item in client.get("/competitions").json()["data"]
        if item["name"] == CUMCM_GD_2026
    )


def test_math_modeling_lists_three_recruiting_teams(client):
    competition = _math_modeling(client)
    teams = client.get(f"/competitions/{competition['id']}/teams").json()["data"]
    titles = {item["title"] for item in teams}
    assert titles == {"数模组队差建模", "数模组队差编程", "数模组队差两人"}
    by_title = {item["title"]: item for item in teams}

    modeling = by_title["数模组队差建模"]
    assert modeling["member_count"] == 2
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
    assert "GATHERING_PRIVACY_CHANGED" not in joined.text

