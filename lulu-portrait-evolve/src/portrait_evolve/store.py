"""Append-only event log. The portrait is a projection and can always be replayed."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from portrait_evolve.engine import IngestResult, LivingPortraitEngine
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.portrait import Portrait

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_user_time
    ON events (user_id, occurred_at, event_id);

CREATE TABLE IF NOT EXISTS portraits (
    user_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TEXT
);
"""


class PortraitStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.engine = LivingPortraitEngine()
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def ingest(self, event: BehaviorEvent) -> IngestResult:
        if self._has_event(event.event_id):
            portrait = self.get(event.user_id) or Portrait(user_id=event.user_id)
            return IngestResult(False, False, True, portrait, {})
        portrait = self.get(event.user_id) or Portrait(user_id=event.user_id)
        result = self.engine.apply(portrait, event)
        self._conn.execute(
            "INSERT INTO events (event_id, user_id, occurred_at, payload) VALUES (?, ?, ?, ?)",
            (event.event_id, event.user_id, event.occurred_at, json.dumps(event.to_dict(), ensure_ascii=False)),
        )
        self._save(result.portrait)
        self._conn.commit()
        return result

    def ingest_many(self, events: list[BehaviorEvent]) -> list[IngestResult]:
        return [self.ingest(event) for event in events]

    def get(self, user_id: str) -> Portrait | None:
        row = self._conn.execute(
            "SELECT payload FROM portraits WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return Portrait.from_dict(json.loads(row["payload"]))

    def events(self, user_id: str) -> list[BehaviorEvent]:
        rows = self._conn.execute(
            "SELECT payload FROM events WHERE user_id = ? ORDER BY occurred_at, event_id",
            (user_id,),
        ).fetchall()
        return [BehaviorEvent.from_dict(json.loads(row["payload"])) for row in rows]

    def replay(self, user_id: str) -> Portrait:
        portrait = self.engine.replay(user_id, self.events(user_id))
        self._save(portrait)
        self._conn.commit()
        return portrait

    def _has_event(self, event_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return row is not None

    def _save(self, portrait: Portrait) -> None:
        self._conn.execute(
            """
            INSERT INTO portraits (user_id, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (
                portrait.user_id,
                json.dumps(portrait.to_dict(), ensure_ascii=False),
                portrait.updated_at,
            ),
        )
