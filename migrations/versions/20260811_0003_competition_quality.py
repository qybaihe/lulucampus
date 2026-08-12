"""Add competition quality and action metadata.

Revision ID: 20260811_0003
Revises: 20260811_0002
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0003"
down_revision: str | None = "20260811_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


COLUMNS = [
    sa.Column("participation_mode", sa.String(length=32), nullable=False, server_default="team"),
    sa.Column("registration_mode", sa.String(length=32), nullable=False, server_default="direct"),
    sa.Column("registration_instructions", sa.Text(), nullable=True),
    sa.Column("fee_note", sa.Text(), nullable=True),
    sa.Column("recommendation_tier", sa.String(length=1), nullable=False, server_default="B"),
    sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
]


def _column_names() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("competition_events")}


def upgrade() -> None:
    existing = _column_names()
    for column in COLUMNS:
        if column.name not in existing:
            op.add_column("competition_events", column)
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("competition_events")}
    if "ix_competition_events_recommendation_tier" not in indexes:
        op.create_index(
            "ix_competition_events_recommendation_tier",
            "competition_events",
            ["recommendation_tier"],
        )


def downgrade() -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("competition_events")}
    if "ix_competition_events_recommendation_tier" in indexes:
        op.drop_index("ix_competition_events_recommendation_tier", table_name="competition_events")
    existing = _column_names()
    for column in reversed(COLUMNS):
        if column.name in existing:
            op.drop_column("competition_events", column.name)
