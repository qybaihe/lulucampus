"""Add phone + password_hash columns to users for phone/password auth.

Revision ID: 20260812_0019
Revises: 20260812_0018
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0019"
down_revision: str | None = "20260812_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "phone" not in columns:
        op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))
        op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    if "password_hash" not in columns:
        op.add_column(
            "users", sa.Column("password_hash", sa.String(length=256), nullable=True)
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "phone" in columns:
        op.drop_index("ix_users_phone", table_name="users")
        op.drop_column("users", "phone")
    if "password_hash" in columns:
        op.drop_column("users", "password_hash")
