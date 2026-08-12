"""Persist private matching self-report preferences.

Revision ID: 20260811_0012
Revises: 20260811_0011
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0012"
down_revision: str | None = "20260811_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("users")}
    if "matching_preferences" not in columns:
        with op.batch_alter_table("users") as batch:
            batch.add_column(
                sa.Column(
                    "matching_preferences",
                    sa.JSON(),
                    nullable=False,
                    server_default=sa.text(
                        "'{\"interaction_style\":\"balanced\","
                        "\"sport_level\":\"casual\","
                        "\"study_intensity\":\"balanced\"}'"
                    ),
                )
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("users")}
    if "matching_preferences" in columns:
        with op.batch_alter_table("users") as batch:
            batch.drop_column("matching_preferences")
