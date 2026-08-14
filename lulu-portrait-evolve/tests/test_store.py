from __future__ import annotations

from portrait_evolve.events import BehaviorEvent
from portrait_evolve.store import PortraitStore


def _event(event_id: str, **kwargs) -> BehaviorEvent:
    raw = {
        "event_id": event_id,
        "user_id": "u1",
        "type": "complete_gathering",
        "occurred_at": "2026-08-01T20:00:00+08:00",
        "scene": "运动搭子",
        "text": "羽毛球",
    }
    raw.update(kwargs)
    return BehaviorEvent.from_dict(raw)


def test_duplicate_event_id_is_ignored():
    store = PortraitStore()
    first = store.ingest(_event("same"))
    second = store.ingest(_event("same"))
    assert first.applied is True
    assert second.duplicate is True
    assert second.applied is False
    assert store.get("u1").event_count == 1


def test_replay_rebuilds_the_same_projection():
    store = PortraitStore()
    store.ingest(_event("a", occurred_at="2026-07-01T20:00:00+08:00"))
    store.ingest(_event("b", occurred_at="2026-07-08T20:00:00+08:00", type="recur_gathering"))
    live = store.get("u1")
    rebuilt = store.replay("u1")
    assert rebuilt.public_view()["scenes"] == live.public_view()["scenes"]
    assert rebuilt.primary_tag.key == live.primary_tag.key


def test_late_exit_shrinks_scene_not_identity():
    store = PortraitStore()
    store.ingest(_event("done"))
    before = store.get("u1").lived.scenes["运动搭子"].score
    store.ingest(
        _event(
            "exit",
            type="late_exit",
            occurred_at="2026-08-01T21:00:00+08:00",
        )
    )
    after = store.get("u1")
    assert after.lived.scenes["运动搭子"].score < before
    assert after.primary_tag is not None
