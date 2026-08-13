from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.core.time import ensure_utc
from onemore.db.models import (
    AuthorizationGrant,
    CompetitionEvent,
    CompetitionStatus,
    IntentCard,
    IntentStatus,
    SessionHealth,
    TrustProfile,
    User,
    utcnow,
)
from onemore.hermes.executor import executor_pool
from onemore.modules.collab.service import archive_spaces, evaluate_goal_reminders
from onemore.modules.competitions.service import expire_sweep as expire_competitions
from onemore.modules.gathering.service import (
    adjudicate_overdue_completion_outcomes,
    dissolve_expired,
    expire_confirmations,
    schedule_completion_confirmations,
    start_due_gatherings,
)
from onemore.modules.intent.service import expire_sweep as expire_intents
from onemore.modules.matching.service import run_matching
from onemore.modules.notify.service import (
    drain_push_outbox,
    push,
    schedule_campus_reminders,
    schedule_gathering_reminders,
)
from onemore.modules.profile.service import init_profile
from onemore.modules.schedule.orchestrator import refresh_user_timetable
from onemore.modules.trust.service import recompute_level, restore
from onemore.tasks.celery_app import celery_app


@celery_app.task(name="onemore.identity.login", time_limit=220, soft_time_limit=215)
def identity_login(session_id: str) -> None:
    from onemore.hermes.login import login_orchestrator

    login_orchestrator.run(session_id)


@celery_app.task(name="onemore.profile.initialize")
def profile_initialize(user_id: str) -> None:
    with SessionLocal() as db:
        init_profile(db, user_id)


@celery_app.task(name="onemore.matching.run")
def matching_run() -> dict:
    with SessionLocal() as db:
        return run_matching(db)


@celery_app.task(name="onemore.schedule.refresh_user")
def schedule_refresh_user(user_id: str) -> dict:
    return refresh_user_timetable(user_id)


@celery_app.task(name="onemore.intent.expire")
def intent_expire() -> dict:
    with SessionLocal() as db:
        return {"expired": expire_intents(db)}


@celery_app.task(name="onemore.gathering.confirmation_timeout")
def confirmation_timeout() -> dict:
    with SessionLocal() as db:
        completion_outcomes = adjudicate_overdue_completion_outcomes(db)
        return {
            "timed_out_members": expire_confirmations(db),
            "dissolved": dissolve_expired(db),
            "started": start_due_gatherings(db),
            "completion_prompts": schedule_completion_confirmations(db),
            "completion_outcomes": completion_outcomes,
        }


@celery_app.task(name="onemore.notify.reminders")
def reminders() -> dict:
    with SessionLocal() as db:
        gathering = schedule_gathering_reminders(db)
        campus = schedule_campus_reminders(db)
        return {
            "sent": gathering + campus,
            "gathering": gathering,
            "campus": campus,
        }


@celery_app.task(name="onemore.notify.deliver_outbox")
def notify_deliver_outbox() -> dict:
    with SessionLocal() as db:
        return drain_push_outbox(db)


@celery_app.task(name="onemore.identity.health_check")
def health_check() -> dict:
    with SessionLocal() as db:
        rows = list(db.scalars(select(SessionHealth)))
        for row in rows:
            healthy, category = executor_pool.check_subsystem(row.user_id, row.subsystem)
            row.healthy = healthy
            row.error_category = category
            row.last_checked_at = utcnow()
        db.commit()
        return {
            "checked": len(rows),
            "unhealthy": sum(not row.healthy for row in rows),
        }


@celery_app.task(name="onemore.trust.recompute_all")
def trust_recompute_all() -> dict:
    with SessionLocal() as db:
        user_ids = list(db.scalars(select(User.id)))
        restored = 0
        for user_id in user_ids:
            profile = db.get(TrustProfile, user_id)
            if (
                profile
                and profile.observation_until
                and ensure_utc(profile.observation_until) <= datetime.now(UTC)
            ):
                restore(db, user_id)
                restored += 1
            else:
                recompute_level(db, user_id)
        return {"recomputed": len(user_ids), "restored": restored}


@celery_app.task(name="onemore.collab.archive_spaces")
def collab_archive_spaces() -> dict:
    with SessionLocal() as db:
        return {"archived": archive_spaces(db)}


@celery_app.task(name="onemore.collab.goal_reminders")
def collab_goal_reminders() -> dict:
    with SessionLocal() as db:
        sent = evaluate_goal_reminders(db)
        db.commit()
        return {"sent": sent}


@celery_app.task(name="onemore.competitions.expire")
def competitions_expire() -> dict:
    with SessionLocal() as db:
        return {"expired": expire_competitions(db)}


@celery_app.task(name="onemore.competitions.deadline_reminders")
def competition_deadline_reminders() -> dict:
    with SessionLocal() as db:
        deadline = datetime.now(UTC) + timedelta(days=3)
        competitions = list(
            db.scalars(
                select(CompetitionEvent).where(
                    CompetitionEvent.status == CompetitionStatus.ACTIONABLE.value,
                    CompetitionEvent.registration_deadline <= deadline,
                    CompetitionEvent.registration_deadline > datetime.now(UTC),
                )
            )
        )
        sent = 0
        for competition in competitions:
            if competition.registration_deadline is None:
                continue
            intents = list(
                db.scalars(
                    select(IntentCard).where(
                        IntentCard.competition_id == competition.id,
                        IntentCard.status.in_(
                            [IntentStatus.POOLING.value, IntentStatus.MATCHED.value]
                        ),
                    )
                )
            )
            for intent in intents:
                push(
                    db,
                    intent.user_id,
                    "competition_deadline",
                    {
                        "competition_id": competition.id,
                        "deadline": competition.registration_deadline.isoformat(),
                        "deep_link": f"onemore://competition/{competition.id}",
                        "summary": f"「{competition.name}」报名即将截止",
                    },
                    dedupe_key=f"competition-deadline:{competition.id}",
                )
                sent += 1
        db.commit()
        return {"sent": sent}


@celery_app.task(name="onemore.schedule.weekly_delta")
def schedule_weekly_delta() -> dict:
    with SessionLocal() as db:
        user_ids = list(
            db.scalars(
                select(AuthorizationGrant.user_id).where(
                    AuthorizationGrant.scope == "timetable",
                    AuthorizationGrant.granted.is_(True),
                )
            )
        )
    results = [refresh_user_timetable(user_id) for user_id in user_ids]
    return {
        "checked": len(results),
        "changed": sum(bool(item.get("changed")) for item in results),
        "failed": sum(not item.get("ok", False) for item in results),
    }


@celery_app.task(name="onemore.cast_driver.tick")
def cast_driver_tick() -> dict:
    from onemore.modules.cast_driver.service import tick

    with SessionLocal() as db:
        return tick(db)
