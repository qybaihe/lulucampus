"""Record successful Douyin mobile verification separately from collection.

Revision ID: 20260811_0004
Revises: 20260811_0003
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0004"
down_revision: str | None = "20260811_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns("taste_import_sessions")
    return any(column["name"] == name for column in columns)


def upgrade() -> None:
    if _has_column("authenticated_at"):
        return
    with op.batch_alter_table("taste_import_sessions") as batch_op:
        batch_op.add_column(sa.Column("authenticated_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    if not _has_column("authenticated_at"):
        return
    with op.batch_alter_table("taste_import_sessions") as batch_op:
        batch_op.drop_column("authenticated_at")
