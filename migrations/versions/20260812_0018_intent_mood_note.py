"""Add the anonymous one-line mood note to intent cards.

Revision ID: 20260812_0018
Revises: 20260811_0017
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0018"
down_revision: str | None = "20260811_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "intent_cards" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("intent_cards")}
    if "mood_note" not in columns:
        op.add_column(
            "intent_cards",
            sa.Column("mood_note", sa.String(length=120), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "intent_cards" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("intent_cards")}
    if "mood_note" in columns:
        op.drop_column("intent_cards", "mood_note")
