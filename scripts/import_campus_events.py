#!/usr/bin/env python3
"""Import campus events JSON into external_events (idempotent upsert by external_key).

JSON fields match the ExternalEvent contract; starts_at/ends_at may be ISO-8601 with
offset (e.g. +08:00). This script converts aware datetimes to naive UTC for SQLite.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

# Ensure project root is importable when run as scripts/import_campus_events.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from onemore.core.database import SessionLocal  # noqa: E402
from onemore.db.models import ExternalEvent  # noqa: E402

ALLOWED_SOURCES = frozenset(
    {"讲座", "演出", "赛事", "社团", "招新", "宣讲", "宣讲会", "招聘", "招聘会", "其他"}
)
DEMO_EXTERNAL_KEYS = frozenset(
    {
        "demo-teachin-1",
        "demo-seminar-1",
        "demo-club-dance-1",
        "demo-club-photo-1",
        "demo-club-recruit-1",
        "demo-club-drama-1",
        "demo-club-frisbee-1",
        "demo-talk-baoyan-1",
    }
)


def _to_naive_utc(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        # Assume already UTC naive if no offset provided
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def _load_events(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"expected JSON array in {path}")
    events: list[dict[str, Any]] = []
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise SystemExit(f"row {i}: expected object")
        for key in ("source", "external_key", "title", "official_url"):
            if key not in row:
                raise SystemExit(f"row {i}: missing required field {key!r}")
        source = str(row["source"]).strip()
        if source not in ALLOWED_SOURCES:
            raise SystemExit(
                f"row {i}: source {source!r} not in {sorted(ALLOWED_SOURCES)}"
            )
        external_key = str(row["external_key"]).strip()
        if not external_key or len(external_key) > 128:
            raise SystemExit(f"row {i}: invalid external_key")
        title = str(row["title"]).strip()
        if not title or len(title) > 256:
            raise SystemExit(f"row {i}: invalid title")
        official_url = row.get("official_url")
        if official_url is None:
            official_url = ""
        official_url = str(official_url)
        location = row.get("location")
        if location is not None:
            location = str(location).strip() or None
            if location and len(location) > 256:
                raise SystemExit(f"row {i}: location too long")
        details = row.get("details") or {}
        if not isinstance(details, dict):
            raise SystemExit(f"row {i}: details must be an object")
        events.append(
            {
                "source": source,
                "external_key": external_key,
                "title": title,
                "starts_at": _to_naive_utc(row.get("starts_at")),
                "ends_at": _to_naive_utc(row.get("ends_at")),
                "location": location,
                "official_url": official_url,
                "details": details,
            }
        )
    return events


def import_events(
    path: Path,
    *,
    remove_demo: bool = True,
    dry_run: bool = False,
) -> dict[str, int]:
    rows = _load_events(path)
    inserted = updated = skipped = removed_demo = 0

    with SessionLocal() as db:
        if remove_demo:
            demos = list(
                db.scalars(
                    select(ExternalEvent).where(
                        ExternalEvent.external_key.in_(DEMO_EXTERNAL_KEYS)
                    )
                )
            )
            for item in demos:
                if not dry_run:
                    db.delete(item)
                removed_demo += 1

        for row in rows:
            existing = db.scalar(
                select(ExternalEvent).where(
                    ExternalEvent.external_key == row["external_key"]
                )
            )
            if existing is None:
                if not dry_run:
                    db.add(
                        ExternalEvent(
                            source=row["source"],
                            external_key=row["external_key"],
                            title=row["title"],
                            starts_at=row["starts_at"],
                            ends_at=row["ends_at"],
                            location=row["location"],
                            official_url=row["official_url"],
                            details=row["details"],
                        )
                    )
                inserted += 1
                continue

            changed = False
            for field in (
                "source",
                "title",
                "starts_at",
                "ends_at",
                "location",
                "official_url",
                "details",
            ):
                if getattr(existing, field) != row[field]:
                    if not dry_run:
                        setattr(existing, field, row[field])
                    changed = True
            if changed:
                updated += 1
            else:
                skipped += 1

        if not dry_run:
            db.commit()

    return {
        "total_json": len(rows),
        "inserted": inserted,
        "updated": updated,
        "unchanged": skipped,
        "removed_demo": removed_demo,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        default=ROOT / "data/campus-events/2026-09.json",
        help="Path to campus events JSON array",
    )
    parser.add_argument(
        "--keep-demo",
        action="store_true",
        help="Do not delete demo-teachin-1 / demo-seminar-1 rows",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report counts without writing",
    )
    args = parser.parse_args()
    path = args.file.expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"file not found: {path}")

    stats = import_events(
        path,
        remove_demo=not args.keep_demo,
        dry_run=args.dry_run,
    )
    mode = "dry_run" if args.dry_run else "committed"
    print(f"mode={mode} file={path}")
    for key, value in stats.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
