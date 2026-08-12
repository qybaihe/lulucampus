"""Add automatic shared-goal progress and private recurrence choices.

Revision ID: 20260811_0013
Revises: 20260811_0012
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0013"
down_revision: str | None = "20260811_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    goal_columns = {item["name"] for item in inspector.get_columns("shared_goals")}
    with op.batch_alter_table("shared_goals") as batch:
        if "milestones" not in goal_columns:
            batch.add_column(
                sa.Column(
                    "milestones", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
                )
            )
        if "next_action" not in goal_columns:
            batch.add_column(sa.Column("next_action", sa.String(length=500), nullable=True))
        if "last_broadcast" not in goal_columns:
            batch.add_column(sa.Column("last_broadcast", sa.Text(), nullable=True))
        if "last_progress_at" not in goal_columns:
            batch.add_column(sa.Column("last_progress_at", sa.DateTime(timezone=True)))

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "shared_goal_member_progress" not in tables:
        op.create_table(
            "shared_goal_member_progress",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("goal_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("current_value", sa.Float(), nullable=False, server_default="0"),
            sa.Column("source_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("last_progress_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["goal_id"], ["shared_goals.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("goal_id", "user_id"),
        )
        op.create_index(
            "ix_shared_goal_member_progress_goal_id",
            "shared_goal_member_progress",
            ["goal_id"],
        )
        op.create_index(
            "ix_shared_goal_member_progress_user_id",
            "shared_goal_member_progress",
            ["user_id"],
        )

    if "gathering_recurrence_decisions" not in tables:
        op.create_table(
            "gathering_recurrence_decisions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("gathering_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("decision", sa.String(length=32), nullable=False),
            sa.Column("kept_user_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("clone_gathering_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["clone_gathering_id"], ["gatherings.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["gathering_id"], ["gatherings.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("gathering_id", "user_id"),
        )
        op.create_index(
            "ix_gathering_recurrence_decisions_gathering_id",
            "gathering_recurrence_decisions",
            ["gathering_id"],
        )
        op.create_index(
            "ix_gathering_recurrence_decisions_user_id",
            "gathering_recurrence_decisions",
            ["user_id"],
        )


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "gathering_recurrence_decisions" in tables:
        op.drop_index(
            "ix_gathering_recurrence_decisions_user_id",
            table_name="gathering_recurrence_decisions",
        )
        op.drop_index(
            "ix_gathering_recurrence_decisions_gathering_id",
            table_name="gathering_recurrence_decisions",
        )
        op.drop_table("gathering_recurrence_decisions")
    if "shared_goal_member_progress" in tables:
        op.drop_index(
            "ix_shared_goal_member_progress_user_id",
            table_name="shared_goal_member_progress",
        )
        op.drop_index(
            "ix_shared_goal_member_progress_goal_id",
            table_name="shared_goal_member_progress",
        )
        op.drop_table("shared_goal_member_progress")
    goal_columns = {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns("shared_goals")
    }
    with op.batch_alter_table("shared_goals") as batch:
        for column in ("last_progress_at", "last_broadcast", "next_action", "milestones"):
            if column in goal_columns:
                batch.drop_column(column)
