from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from onemore.core.database import SessionLocal
from onemore.db.models import CompetitionEvent, CompetitionStatus
from onemore.modules.competitions import service as competition_service
from onemore.modules.competitions.schemas import CompetitionSnapshot


def test_public_competitions_only_contain_verified_actionable_items(client):
    response = client.get("/competitions")
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 24
    assert all(item["name"] != "2026 校园创新应用大赛" for item in items)
    assert all(item["registration_url"].startswith("https://") for item in items)
    assert sum(item["team_forming_supported"] for item in items) == 17
    assert sum(item["collaboration_action"] == "prep_partner" for item in items) == 7
    assert sum(item["recommendation_tier"] == "A" for item in items) == 14
    assert sum(item["recommendation_tier"] == "B" for item in items) == 6
    assert sum(item["recommendation_tier"] == "C" for item in items) == 4
    assert sum(item["recommendation_label"] == "优先推荐" for item in items) == 14
    assert sum(item["recommendation_label"] == "可报名" for item in items) == 6
    assert sum(item["recommendation_label"] == "补充参考" for item in items) == 4
    assert all(item["recommendation_description"] for item in items)
    paths = client.get("/openapi.json").json()["paths"]
    assert not any("signup" in path or "apply" in path for path in paths if "competition" in path)
    assert "/competitions/recommendation-tiers" in paths


def test_recommendation_tier_catalog_is_user_facing(client):
    response = client.get("/competitions/recommendation-tiers")
    assert response.status_code == 200
    tiers = response.json()["data"]
    assert [item["code"] for item in tiers] == ["A", "B", "C"]
    assert [item["label"] for item in tiers] == ["优先推荐", "可报名", "补充参考"]
    assert all(item["description"] for item in tiers)
    assert [item["sort_order"] for item in tiers] == [0, 1, 2]


def test_ingestion_is_idempotent_and_rejects_unverified(client, admin_headers):
    payload = json.loads(Path("fixtures/competition_snapshot.json").read_text())
    first = client.post("/internal/competitions/ingest", headers=admin_headers, json=payload)
    second = client.post("/internal/competitions/ingest", headers=admin_headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["accepted"] == 1
    assert first.json()["data"]["rejected_unverified"] == 1
    public_items = client.get("/competitions").json()["data"]
    assert len(public_items) == 24
    assert all(item["name"] != "2026 校园创新应用大赛" for item in public_items)


def test_unknown_skill_rolls_back_entire_snapshot(client, admin_headers):
    payload = json.loads(Path("fixtures/competition_snapshot.json").read_text())
    payload["snapshot_version"] = "bad-version"
    payload["items"][0]["external_key"] = "bad-competition"
    payload["items"][0]["required_skills"] = ["not_in_course_tag_space"]
    response = client.post("/internal/competitions/ingest", headers=admin_headers, json=payload)
    assert response.status_code == 422
    names = [item["name"] for item in client.get("/competitions").json()["data"]]
    assert len(names) == 24
    assert "2026 校园创新应用大赛" not in names


def test_competition_intent_uses_verified_skills_and_team_constraints(client, auth_headers):
    competition = next(
        item
        for item in client.get("/competitions").json()["data"]
        if item["name"] == "2026全国大学生智能应用开发大赛"
    )
    response = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={"text": "想参加这个比赛", "competition_id": competition["id"]},
    )
    assert response.status_code == 200
    card = response.json()["data"]["card"]
    assert card["mode"] == "complementary"
    # The competition accepts two-person teams, but this demo user's explicit
    # privacy floor is three; compilation must never lower that preference.
    assert card["min_size"] == 3
    assert card["target_size"] == 10
    assert set(card["required_roles"]) == {
        "machine_learning",
        "product",
        "design",
        "operations",
    }


def test_db_ready_snapshot_has_complete_quality_metadata():
    payload = json.loads(
        Path("fixtures/competition_snapshot_2026-08-11_v1.1.json").read_text()
    )
    snapshot = CompetitionSnapshot.model_validate(payload)
    assert len(snapshot.items) == 24
    assert {item.recommendation_tier for item in snapshot.items} == {"A", "B", "C"}
    assert all(item.verified_at is not None for item in snapshot.items)
    assert all(item.registration_instructions for item in snapshot.items)
    assert sum(item.team_size_max > 1 for item in snapshot.items) == 17

    by_key = {item.external_key: item for item in snapshot.items}
    programming = by_key["ncccu_programming_2026"]
    assert "600元/名" in (programming.rewards or "")
    assert "1000元/队" not in (programming.rewards or "")
    international = by_key["waiyanshe_international_communication_sysu_2026"]
    assert international.registration_deadline.isoformat() == "2026-09-13T23:59:00+08:00"


def test_db_ready_snapshot_can_drive_team_and_tier_filters(client, admin_headers):
    payload = json.loads(
        Path("fixtures/competition_snapshot_2026-08-11_v1.1.json").read_text()
    )
    response = client.post("/internal/competitions/ingest", headers=admin_headers, json=payload)
    assert response.status_code == 200
    assert response.json()["data"]["accepted"] == 24

    all_items = client.get("/competitions").json()["data"]
    assert len(all_items) == 24
    assert all(item["registration_deadline"].endswith("Z") for item in all_items)
    assert all(item["verified_at"].endswith("Z") for item in all_items)
    assert sum(item["team_forming_supported"] for item in all_items) == 17
    assert sum(item["collaboration_action"] == "prep_partner" for item in all_items) == 7

    tier_a = client.get("/competitions", params={"recommendation_tier": "A"})
    assert tier_a.status_code == 200
    assert len(tier_a.json()["data"]) == 14


def test_individual_competition_creates_prep_partner_intent(
    client, admin_headers, auth_headers
):
    payload = json.loads(
        Path("fixtures/competition_snapshot_2026-08-11_v1.1.json").read_text()
    )
    client.post("/internal/competitions/ingest", headers=admin_headers, json=payload)
    competition = next(
        item for item in client.get("/competitions").json()["data"] if "程序设计挑战赛" in item["name"]
    )
    assert competition["team_forming_supported"] is False
    response = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={"text": "想参加这个比赛", "competition_id": competition["id"]},
    )
    assert response.status_code == 200
    card = response.json()["data"]["card"]
    assert card["gathering_type"] == "比赛备赛搭子"
    assert card["mode"] == "similar"
    assert card["min_size"] == 3
    assert card["target_size"] == 3


def test_optional_team_competition_never_creates_a_one_person_group(
    client, admin_headers, auth_headers
):
    payload = json.loads(
        Path("fixtures/competition_snapshot_2026-08-11_v1.1.json").read_text()
    )
    client.post("/internal/competitions/ingest", headers=admin_headers, json=payload)
    competition = next(
        item for item in client.get("/competitions").json()["data"] if "人工智能挑战赛" in item["name"]
    )
    response = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={"text": "想参加这个比赛", "competition_id": competition["id"]},
    )
    assert response.status_code == 200
    card = response.json()["data"]["card"]
    assert card["gathering_type"] == "比赛组队"
    assert card["mode"] == "complementary"
    assert card["min_size"] == 3
    assert card["target_size"] == 3


def test_registration_deadline_expires_public_entry_even_when_submission_is_later(client):
    competition_id = client.get("/competitions").json()["data"][0]["id"]
    with SessionLocal() as db:
        event = db.get(CompetitionEvent, competition_id)
        assert event is not None
        event.registration_deadline = datetime.now(UTC) - timedelta(minutes=1)
        event.submission_deadline = datetime.now(UTC) + timedelta(days=30)
        db.commit()
        assert competition_service.expire_sweep(db) == 1
        assert event.status == CompetitionStatus.EXPIRED.value
    remaining = client.get("/competitions").json()["data"]
    assert len(remaining) == 23
    assert competition_id not in {item["id"] for item in remaining}
