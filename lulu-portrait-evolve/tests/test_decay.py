from __future__ import annotations

from datetime import datetime, timezone

from portrait_evolve.engine import decay


def test_half_life_halves_the_score():
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    later = datetime(2026, 7, 31, tzinfo=timezone.utc)
    # 60-day half-life, ~60 days later
    value = decay(0.8, start.isoformat(), later, 60.0)
    assert 0.38 < value < 0.42


def test_missing_timestamp_does_not_decay():
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert decay(0.7, None, now, 60.0) == 0.7


def test_decay_is_incremental_not_compounded():
    from portrait_evolve.engine import LivingPortraitEngine
    from portrait_evolve.events import BehaviorEvent
    from portrait_evolve.portrait import Portrait

    engine = LivingPortraitEngine()
    portrait = Portrait(user_id="u1")
    engine.apply(
        portrait,
        BehaviorEvent.from_dict(
            {
                "event_id": "seed",
                "user_id": "u1",
                "type": "seed_academic",
                "occurred_at": "2026-01-01T00:00:00+00:00",
                "skills": ["backend"],
            }
        ),
    )
    engine.apply(
        portrait,
        BehaviorEvent.from_dict(
            {
                "event_id": "a",
                "user_id": "u1",
                "type": "browse_competition",
                "occurred_at": "2026-07-01T00:00:00+00:00",
                "text": "看看",
            }
        ),
    )
    mid = portrait.academic.skills["backend"].score
    engine.apply(
        portrait,
        BehaviorEvent.from_dict(
            {
                "event_id": "b",
                "user_id": "u1",
                "type": "browse_competition",
                "occurred_at": "2026-07-01T00:10:00+00:00",
                "text": "再看看",
            }
        ),
    )
    assert abs(portrait.academic.skills["backend"].score - mid) < 0.01
