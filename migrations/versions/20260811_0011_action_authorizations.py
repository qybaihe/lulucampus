"""Require every current member to authorize one immutable action preview.

Revision ID: 20260811_0011
Revises: 20260811_0010
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0011"
down_revision: str | None = "20260811_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "action_authorizations" in inspector.get_table_names():
        return
    op.create_table(
        "action_authorizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["action_id"], ["campus_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action_id", "user_id"),
    )
    op.create_index(
        op.f("ix_action_authorizations_action_id"),
        "action_authorizations",
        ["action_id"],
    )
    op.create_index(
        op.f("ix_action_authorizations_user_id"),
        "action_authorizations",
        ["user_id"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "action_authorizations" not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_action_authorizations_user_id"), table_name="action_authorizations")
    op.drop_index(op.f("ix_action_authorizations_action_id"), table_name="action_authorizations")
    op.drop_table("action_authorizations")
