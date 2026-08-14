from __future__ import annotations

import json
from pathlib import Path

from portrait_evolve.engine import LivingPortraitEngine
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.explain import explain
from portrait_evolve.portrait import Portrait

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "linyuan_timeline.json"


def _event(**kwargs) -> BehaviorEvent:
    base = {
        "event_id": "e1",
        "user_id": "u1",
        "type": "post_intent",
        "occurred_at": "2026-08-01T12:00:00+08:00",
    }
    base.update(kwargs)
    return BehaviorEvent.from_dict(base)


def test_behavior_outweighs_stale_taste_without_wiping_academic():
    engine = LivingPortraitEngine()
    portrait = Portrait(user_id="u1")
    engine.apply(
        portrait,
        _event(
            event_id="seed-a",
            type="seed_academic",
                occurred_at="2026-06-28T09:00:00+08:00",
                skills=["backend"],
                domains=["ai_programming"],
            ),
        )
    engine.apply(
        portrait,
        _event(
            event_id="seed-t",
            type="seed_taste",
            occurred_at="2026-06-28T09:01:00+08:00",
            domains=["visual_creation"],
            payload={"tags": {"aesthetic_observer": 0.4}, "signals": {"aesthetic": 0.6}},
        ),
    )
    academic_backend = portrait.academic.skills["backend"].score
    academic_hits = portrait.academic.skills["backend"].hits
    for index in range(4):
        engine.apply(
            portrait,
            _event(
                event_id=f"hack-{index}",
                type="complete_gathering",
                occurred_at=f"2026-07-0{index + 1}T20:00:00+08:00",
                scene="比赛组队",
                competition="智能应用开发大赛",
                roles_offered=["backend"],
                text="黑客松完赛",
            ),
        )
    assert portrait.academic.skills["backend"].hits == academic_hits
    assert portrait.academic.skills["backend"].score > academic_backend * 0.95
    assert portrait.lived.domains["ai_programming"].score > 0.5
    assert portrait.lived.scenes["比赛组队"].score > 0.5
    assert portrait.primary_tag is not None
    assert portrait.primary_tag.key in {"explorer_builder", "ai_practitioner", "growth_driver"}


def test_seeking_a_role_does_not_claim_that_skill():
    engine = LivingPortraitEngine()
    portrait = Portrait(user_id="u1")
    engine.apply(
        portrait,
        _event(
            type="seek_teammate",
            scene="比赛组队",
            roles_offered=["backend"],
            roles_sought=["frontend", "product"],
            text="我做后端，缺前端和产品",
        ),
    )
    assert "backend" in portrait.lived.skills
    assert "frontend" not in portrait.lived.skills
    assert "frontend" in portrait.lived.roles_sought
    assert "product" in portrait.lived.roles_sought


def test_primary_tag_uses_hysteresis():
    engine = LivingPortraitEngine()
    portrait = Portrait(user_id="u1")
    engine.apply(
        portrait,
        _event(
            event_id="seed",
            type="seed_taste",
            payload={"tags": {"explorer_builder": 0.4}, "domains": {"ai_programming": 0.4}},
            domains=["ai_programming"],
        ),
    )
    first = portrait.primary_tag.key if portrait.primary_tag else None
    engine.apply(
        portrait,
        _event(
            event_id="weak-browse",
            type="browse_competition",
            competition="一场路演",
            text="随便看看创业路演",
        ),
    )
    assert portrait.primary_tag is not None
    assert portrait.primary_tag.key == first


def test_linyuan_timeline_becomes_a_living_portrait():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    events = [BehaviorEvent.from_dict(raw) for raw in payload["events"]]
    portrait = LivingPortraitEngine().replay("u_demo_1", events)
    view = portrait.public_view()
    assert view["event_count"] == len(events)
    assert view["primary_tag"]["key"] in {"explorer_builder", "ai_practitioner"}
    domain_keys = {item["key"] for item in view["interest_domains"]}
    assert "ai_programming" in domain_keys
    assert "health_sports" in domain_keys
    offered = {item["key"] for item in view["roles_offered"]}
    sought = {item["key"] for item in view["roles_sought"]}
    assert "backend" in offered or "data_analysis" in offered
    assert "frontend" in sought or "writing" in sought
    scenes = {item["key"] for item in view["scenes"]}
    assert "比赛组队" in scenes
    assert "运动搭子" in scenes
    report = explain(portrait, events)
    assert any("比赛" in line or "局" in line for line in report["why"])
    assert portrait.confidence > 0.5
