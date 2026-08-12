"""Make gathering reschedules an anonymous unanimous vote.

Revision ID: 20260811_0015
Revises: 20260811_0014
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0015"
down_revision: str | None = "20260811_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("reschedule_proposals")}
    with op.batch_alter_table("reschedule_proposals") as batch:
        if "eligible_user_ids" not in columns:
            batch.add_column(
                sa.Column(
                    "eligible_user_ids",
                    sa.JSON(),
                    nullable=False,
                    server_default=sa.text("'[]'"),
                )
            )
        if "expires_at" not in columns:
            batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True)))
        if "decided_at" not in columns:
            batch.add_column(sa.Column("decided_at", sa.DateTime(timezone=True)))

    if "reschedule_votes" not in set(sa.inspect(op.get_bind()).get_table_names()):
        op.create_table(
            "reschedule_votes",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("proposal_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("accepted", sa.Boolean(), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["proposal_id"], ["reschedule_proposals.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("proposal_id", "user_id"),
        )
        op.create_index(
            "ix_reschedule_votes_proposal_id", "reschedule_votes", ["proposal_id"]
        )
        op.create_index("ix_reschedule_votes_user_id", "reschedule_votes", ["user_id"])


def downgrade() -> None:
    if "reschedule_votes" in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_index("ix_reschedule_votes_user_id", table_name="reschedule_votes")
        op.drop_index("ix_reschedule_votes_proposal_id", table_name="reschedule_votes")
        op.drop_table("reschedule_votes")
    columns = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("reschedule_proposals")
    }
    with op.batch_alter_table("reschedule_proposals") as batch:
        for name in ("decided_at", "expires_at", "eligible_user_ids"):
            if name in columns:
                batch.drop_column(name)
