from __future__ import annotations

from celery import Celery

from onemore.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "onemore",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["onemore.tasks.jobs"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "matching-every-minute": {
            "task": "onemore.matching.run",
            "schedule": 60.0,
        },
        "intent-expire-every-five-minutes": {
            "task": "onemore.intent.expire",
            "schedule": 300.0,
        },
        "confirmation-timeout-every-minute": {
            "task": "onemore.gathering.confirmation_timeout",
            "schedule": 60.0,
        },
        "reminders-every-five-minutes": {
            "task": "onemore.notify.reminders",
            "schedule": 300.0,
        },
        "push-outbox-every-thirty-seconds": {
            "task": "onemore.notify.deliver_outbox",
            "schedule": 30.0,
        },
        "session-health-every-six-hours": {
            "task": "onemore.identity.health_check",
            "schedule": 21600.0,
        },
        "trust-recompute-daily": {
            "task": "onemore.trust.recompute_all",
            "schedule": 86400.0,
        },
        "spaces-archive-daily": {
            "task": "onemore.collab.archive_spaces",
            "schedule": 86400.0,
        },
        "shared-goal-reminders-daily": {
            "task": "onemore.collab.goal_reminders",
            "schedule": 86400.0,
        },
        "competitions-expire-daily": {
            "task": "onemore.competitions.expire",
            "schedule": 86400.0,
        },
        "competition-deadlines-daily": {
            "task": "onemore.competitions.deadline_reminders",
            "schedule": 86400.0,
        },
        "timetable-delta-weekly": {
            "task": "onemore.schedule.weekly_delta",
            "schedule": 604800.0,
        },
        "cast-driver-every-fifteen-minutes": {
            "task": "onemore.cast_driver.tick",
            "schedule": 900.0,
        },
    },
)
