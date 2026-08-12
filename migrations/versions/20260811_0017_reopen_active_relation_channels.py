"""Repair channels left closed when a dissolved relation was reactivated.

Revision ID: 20260811_0017
Revises: 20260811_0016
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0017"
down_revision: str | None = "20260811_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if not {"channels", "relations"}.issubset(tables):
        return
    op.execute(
        sa.text(
            """
            UPDATE channels
               SET status = 'open', archived_at = NULL
             WHERE relation_id IS NOT NULL
               AND status != 'open'
               AND EXISTS (
                   SELECT 1
                     FROM relations
                    WHERE relations.id = channels.relation_id
                      AND relations.status = 'active'
               )
            """
        )
    )


def downgrade() -> None:
    # This is an invariant repair, not a schema mutation. Restoring the broken
    # active-relation/closed-channel combination would corrupt reachable data.
    pass
