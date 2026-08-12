"""Persist member-requested action preview modifications.

Revision ID: 20260811_0016
Revises: 20260811_0015
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0016"
down_revision: str | None = "20260811_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "action_modifications" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "action_modifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column("requester_user_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("proposed_params", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="requested"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["action_id"], ["campus_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["requester_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_action_modifications_action_id", "action_modifications", ["action_id"]
    )
    op.create_index(
        "ix_action_modifications_requester_user_id",
        "action_modifications",
        ["requester_user_id"],
    )


def downgrade() -> None:
    if "action_modifications" not in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.drop_index(
        "ix_action_modifications_requester_user_id", table_name="action_modifications"
    )
    op.drop_index(
        "ix_action_modifications_action_id", table_name="action_modifications"
    )
    op.drop_table("action_modifications")
