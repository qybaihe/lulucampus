from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.demo_cast import CHEN, HE, LIANG, LIN, ZHOU
from onemore.db.models import CastDriverEvent, Gathering, GatheringStatus
from onemore.modules.cast_driver.service import snapshot, tick
from onemore.modules.gathering import service as gathering_service

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _at(*, weekday: int, hour: int, minute: int = 0) -> datetime:
    """Pick a datetime in the current week with the given weekday/hour in Shanghai."""

    now = datetime.now(SHANGHAI)
    start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    start -= timedelta(days=(start.weekday() - weekday) % 7)
    if start <= now:
        start += timedelta(days=7)
    return start.astimezone(UTC)


def test_tick_disabled_by_default():
    with SessionLocal() as db:
        result = tick(db)
    assert result["skipped"] is True
    assert result["reason"] == "disabled"


def test_status_endpoint_requires_admin(client):
    denied = client.get("/internal/cast-driver/status")
    assert denied.status_code == 403
    ok = client.get("/internal/cast-driver/status", headers={"X-Admin-Token": "test-admin"})
    assert ok.status_code == 200
    body = ok.json()["data"]
    assert body["enabled"] is False
    assert len(body["people"]) == 6


def test_in_class_records_attend_and_skips_publish():
    tuesday_morning = _at(weekday=1, hour=10, minute=30)
    with SessionLocal() as db:
        result = tick(db, now=tuesday_morning, enabled=True, force=True)
        events = list(db.scalars(select(CastDriverEvent).where(CastDriverEvent.kind == "attend_class")))
    kinds = {item["kind"] for item in result["actions"] if not item.get("skipped")}
    assert "attend_class" in kinds
    assert "publish" not in kinds
    assert any(event.user_id == LIN for event in events)
    assert any(event.user_id == ZHOU for event in events)


def test_quiet_hours_skip_proactive_without_force():
    night = _at(weekday=5, hour=2, minute=0)
    with SessionLocal() as db:
        result = tick(db, now=night, enabled=True, force=False)
    assert result["quiet"] is True
    assert all(item["kind"] in {"confirm", "complete", "attend_class"} or item.get("skipped") for item in result["actions"])
    assert not any(item["kind"] in {"publish", "join", "chat"} for item in result["actions"])


def test_publish_goes_through_real_intent_api():
    saturday_evening = _at(weekday=5, hour=20, minute=10)
    with SessionLocal() as db:
        before = {
            item.id
            for item in db.scalars(select(Gathering).where(Gathering.status == GatheringStatus.POOLING.value))
        }
        result = tick(db, now=saturday_evening, enabled=True, force=True)
        published = [item for item in result["actions"] if item["kind"] == "publish"]
        assert published, result
        gathering = db.get(Gathering, published[0]["gathering_id"])
        assert gathering is not None
        assert gathering.id not in before
        assert (gathering.official_metadata or {}).get("created_via") == "cast_driver"


def test_never_joins_reserved_gap_for_real_users():
    saturday_evening = _at(weekday=5, hour=20, minute=10)
    with SessionLocal() as db:
        tick(db, now=saturday_evening, enabled=True, force=True)
        reserved = list(
            db.scalars(select(Gathering).where(Gathering.title.in_(["周六英东羽毛球", "数模组队差建模"])))
        )
        assert reserved
        for gathering in reserved:
            members = gathering_service.active_members(db, gathering.id)
            ids = {member.user_id for member in members}
            if gathering.title == "周六英东羽毛球":
                assert ids == {LIN, HE, LIANG}
            if gathering.title == "数模组队差建模":
                assert ids == {ZHOU, LIN}


def test_daily_publish_cap():
    saturday_evening = _at(weekday=5, hour=20, minute=10)
    with SessionLocal() as db:
        first = tick(db, now=saturday_evening, enabled=True, force=True)
        second = tick(
            db,
            now=saturday_evening + timedelta(minutes=20),
            enabled=True,
            force=True,
        )
    first_publishes = [item for item in first["actions"] if item["kind"] == "publish"]
    second_publishes = [item for item in second["actions"] if item["kind"] == "publish"]
    assert len(first_publishes) <= 1
    if first_publishes:
        owner = first_publishes[0]["user_id"]
        assert owner not in {item["user_id"] for item in second_publishes}


def test_confirm_after_delay(client, admin_headers):
    from tests.cast_helpers import publish_aligned_intent

    text = "周六晚上三个人一起打羽毛球"
    for user_id in (LIN, ZHOU, CHEN):
        publish_aligned_intent(client, user_id, text)
    formed = client.post("/internal/matching/run", headers=admin_headers).json()["data"]
    assert formed.get("gathering_ids"), formed
    later = datetime.now(UTC) + timedelta(hours=3)
    with SessionLocal() as db:
        result = tick(db, now=later, enabled=True, force=True)
    assert any(item["kind"] == "confirm" for item in result["actions"]), result


def test_snapshot_lists_cast():
    with SessionLocal() as db:
        body = snapshot(db)
    names = [person["display_name"] for person in body["people"]]
    assert names == ["林予安", "周衡", "陈可薇", "梁景行", "苏晚宁", "何屿"]


def test_production_never_runs(monkeypatch):
    from onemore.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "cast_driver_enabled", True)
    with SessionLocal() as db:
        result = tick(db, enabled=True, force=True)
    assert result["skipped"] is True
    assert result["reason"] == "production"
