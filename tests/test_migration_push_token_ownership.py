from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa


def test_legacy_duplicate_push_tokens_are_revoked_before_deduplication():
    migration = importlib.import_module(
        "migrations.versions.20260811_0006_push_token_ownership"
    )
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    table = sa.Table(
        "push_devices",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("token_hash", sa.String, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    metadata.create_all(engine)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            table.insert(),
            [
                {
                    "id": "old-a",
                    "user_id": "u_demo_1",
                    "token_hash": "same-token",
                    "active": True,
                    "created_at": now - timedelta(days=2),
                    "updated_at": now - timedelta(days=2),
                },
                {
                    "id": "new-b",
                    "user_id": "u_demo_2",
                    "token_hash": "same-token",
                    "active": True,
                    "created_at": now - timedelta(days=1),
                    "updated_at": now - timedelta(days=1),
                },
            ],
        )
        migration._revoke_and_deduplicate(connection)
        rows = connection.execute(sa.select(table)).mappings().all()
    assert len(rows) == 1
    assert rows[0]["id"] == "new-b"
    assert rows[0]["active"] is False
