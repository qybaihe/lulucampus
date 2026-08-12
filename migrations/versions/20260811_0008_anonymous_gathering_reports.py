"""Allow gathering-level safety reports before participant disclosure.

Revision ID: 20260811_0008
Revises: 20260811_0007
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0008"
down_revision: str | None = "20260811_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.alter_column(
            "reported_user_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )


def downgrade() -> None:
    op.execute("DELETE FROM reports WHERE reported_user_id IS NULL")
    with op.batch_alter_table("reports") as batch:
        batch.alter_column(
            "reported_user_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
