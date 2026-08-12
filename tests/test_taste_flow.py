"""Taste persona should change competition ranking, recruit hints, and match copy."""

from __future__ import annotations

from onemore.modules.taste_profile.competition_match import score_competition


def _ai_persona() -> dict:
    return {
        "primary_tag": {"key": "explorer_builder", "label": "探索型 Builder", "score": 0.8},
        "secondary_tags": [{"key": "ai_practitioner", "label": "AI 实践派", "score": 0.6}],
        "interest_domains": [
            {"key": "ai_programming", "label": "AI / 编程 / 开源", "score": 0.9}
        ],
        "interest_facets": [
            {"domain": "ai_programming", "facet": "hackathon", "label": "黑客松"}
        ],
        "matching_hints": ["组队黑客松"],
        "summary": "爱把比赛当项目打",
    }


def test_score_competition_prefers_matching_tracks():
    persona = _ai_persona()
    ai_comp = {
        "name": "全国大学生智能应用开发大赛",
        "tracks": ["人工智能", "应用开发"],
        "required_skills": [
            {"key": "machine_learning", "label": "机器学习"},
            {"key": "backend", "label": "后端"},
            {"key": "design", "label": "设计"},
        ],
    }
    sports_comp = {
        "name": "校园马拉松补给站策划",
        "tracks": ["体育"],
        "required_skills": [{"key": "operations", "label": "运营"}],
    }
    ai_score = score_competition(persona, ai_comp)
    sports_score = score_competition(persona, sports_comp)
    assert ai_score["taste_fit"] > sports_score["taste_fit"]
    assert ai_score["taste_fit_label"] in {"很适合你", "和你有点像"}
    assert any("设计" in hint for hint in ai_score["recruit_hints"])


def test_public_competition_list_stays_unpersonalized(client):
    items = client.get("/competitions").json()["data"]
    assert items
    assert all(item.get("taste_fit") is None for item in items)
    assert all(item.get("taste_fit_label") is None for item in items)


def test_logged_in_competition_list_uses_seeded_taste(client, auth_headers):
    public = client.get("/competitions").json()["data"]
    personalized = client.get("/competitions", headers=auth_headers).json()["data"]
    assert len(personalized) == len(public)
    fitted = [item for item in personalized if item.get("taste_fit")]
    assert fitted
    assert personalized[0]["taste_fit"] >= fitted[-1]["taste_fit"]
    top = personalized[0]
    assert top["taste_fit_label"] in {"很适合你", "和你有点像"}
    detail = client.get(f"/competitions/{top['id']}", headers=auth_headers).json()["data"]
    assert detail["taste_fit"] == top["taste_fit"]
    assert detail["recruit_hints"]


def test_intent_compile_returns_recruit_hints_for_competition(client, auth_headers):
    competition = next(
        item
        for item in client.get("/competitions").json()["data"]
        if "智能应用" in item["name"]
    )
    response = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={"text": "想参加这个比赛", "competition_id": competition["id"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["card"]["competition_id"] == competition["id"]
    assert data["recruit_hints"] or data["taste_fit_label"]


def test_gathering_looking_for_is_identity_free(client, auth_headers):
    from datetime import UTC, datetime, timedelta

    from onemore.core.database import SessionLocal
    from onemore.db.models import Gathering, GatheringMember, GatheringStatus

    now = datetime.now(UTC)
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            title="智能应用开发组队",
            goal="补一个设计",
            gathering_type="比赛组队",
            mode="complementary",
            status=GatheringStatus.POOLING.value,
            campus="珠海校区",
            target_size=4,
            min_size=3,
            required_roles=["frontend", "design"],
            required_trust_level="T0",
            expires_at=now + timedelta(days=2),
        )
        db.add(gathering)
        db.flush()
        db.add(
            GatheringMember(
                gathering_id=gathering.id,
                user_id="u_demo_1",
                role="backend",
                confirmation_status="confirmed",
            )
        )
        gathering_id = gathering.id
        db.commit()

    share = client.post(f"/gatherings/{gathering_id}/share", headers=auth_headers)
    assert share.status_code == 201, share.text
    data = share.json()["data"]
    assert any("设计" in item or "前端" in item for item in data["looking_for"])
    page = client.get(f"/g/{data['share_token']}")
    assert page.status_code == 200
    assert "这桌还缺" in page.text
    assert "林予安" not in page.text
