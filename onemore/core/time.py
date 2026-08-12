from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    """Normalize ORM datetimes before Python-side comparison.

    PostgreSQL preserves timezone information while SQLite returns naive values
    for ``DateTime(timezone=True)``.  Treat those SQLite values as UTC so the
    same service code behaves identically in development and production.
    """

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)
