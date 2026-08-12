from __future__ import annotations

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import SessionHealth, utcnow
from onemore.hermes.executor import executor_pool
from onemore.modules.schedule.service import weekly_delta_check


def refresh_user_timetable(user_id: str) -> dict:
    payload, error_category = executor_pool.fetch_timetable_import(user_id)
    with SessionLocal() as db:
        health = db.scalar(
            select(SessionHealth).where(
                SessionHealth.user_id == user_id,
                SessionHealth.subsystem == "jwxt",
            )
        )
        if health is None:
            health = SessionHealth(user_id=user_id, subsystem="jwxt")
            db.add(health)
        health.last_checked_at = utcnow()
        health.healthy = error_category is None
        health.error_category = error_category
        if error_category is not None or payload is None:
            db.commit()
            return {"user_id": user_id, "ok": False, "error_category": error_category}
        result = weekly_delta_check(db, user_id, payload)
        return {"user_id": user_id, "ok": True, **result}
