"""Make per-intent safety preferences enforceable.

Revision ID: 20260811_0014
Revises: 20260811_0013
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0014"
down_revision: str | None = "20260811_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    intent_columns = {item["name"] for item in inspector.get_columns("intent_cards")}
    if "same_gender_only" not in intent_columns:
        with op.batch_alter_table("intent_cards") as batch:
            batch.add_column(
                sa.Column(
                    "same_gender_only",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
    gathering_columns = {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns("gatherings")
    }
    if "identity_disclosure" not in gathering_columns:
        with op.batch_alter_table("gatherings") as batch:
            batch.add_column(
                sa.Column(
                    "identity_disclosure",
                    sa.String(length=32),
                    nullable=False,
                    server_default="after_full",
                )
            )
    op.execute(
        sa.text(
            "UPDATE intent_cards SET social_mode = 'after_full' "
            "WHERE social_mode = 'reveal_after_full'"
        )
    )


def downgrade() -> None:
    intent_columns = {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns("intent_cards")
    }
    if "same_gender_only" in intent_columns:
        with op.batch_alter_table("intent_cards") as batch:
            batch.drop_column("same_gender_only")
    gathering_columns = {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns("gatherings")
    }
    if "identity_disclosure" in gathering_columns:
        with op.batch_alter_table("gatherings") as batch:
            batch.drop_column("identity_disclosure")
