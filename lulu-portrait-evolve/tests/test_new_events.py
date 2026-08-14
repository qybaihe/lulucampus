from portrait_evolve.engine import LivingPortraitEngine
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.portrait import Portrait


def test_book_gym_and_elective_move_lived_not_academic():
    engine = LivingPortraitEngine()
    portrait = Portrait(user_id="u1")
    engine.apply(
        portrait,
        BehaviorEvent.from_dict(
            {
                "event_id": "seed",
                "user_id": "u1",
                "type": "seed_academic",
                "occurred_at": "2026-07-01T00:00:00+08:00",
                "skills": ["backend"],
            }
        ),
    )
    academic_hits = portrait.academic.skills["backend"].hits
    engine.apply(
        portrait,
        BehaviorEvent.from_dict(
            {
                "event_id": "gym",
                "user_id": "u1",
                "type": "book_gym",
                "occurred_at": "2026-07-02T00:00:00+08:00",
                "text": "订英东羽毛球",
            }
        ),
    )
    engine.apply(
        portrait,
        BehaviorEvent.from_dict(
            {
                "event_id": "elective",
                "user_id": "u1",
                "type": "enroll_elective",
                "occurred_at": "2026-07-03T00:00:00+08:00",
                "text": "选了跨专业公选",
                "domains": ["knowledge_method"],
            }
        ),
    )
    assert portrait.academic.skills["backend"].hits == academic_hits
    assert portrait.lived.domains["health_sports"].score > 0.1
    assert portrait.lived.domains["knowledge_method"].score > 0.1


def test_peer_ids_accumulate_without_becoming_skills():
    engine = LivingPortraitEngine()
    portrait = Portrait(user_id="u1")
    engine.apply(
        portrait,
        BehaviorEvent.from_dict(
            {
                "event_id": "done",
                "user_id": "u1",
                "type": "complete_gathering",
                "occurred_at": "2026-07-02T00:00:00+08:00",
                "scene": "比赛组队",
                "peer_ids": ["u2"],
                "roles_offered": ["backend"],
            }
        ),
    )
    assert "u2" in portrait.peers
    assert "u2" not in portrait.lived.skills
