"""Make each APNs token belong to exactly one account.

Revision ID: 20260811_0006
Revises: 20260811_0005
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0006"
down_revision: str | None = "20260811_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _revoke_and_deduplicate(bind: sa.Connection) -> None:
    # Historic builds allowed one row per (user, token). A collision's true
    # current owner cannot be proven during an offline migration, so revoke all
    # colliding rows before retaining only the newest record. APNs registration
    # will explicitly reactivate and transfer that canonical row next launch.
    bind.execute(
        sa.text(
            "UPDATE push_devices SET active = false WHERE token_hash IN "
            "(SELECT token_hash FROM push_devices GROUP BY token_hash HAVING COUNT(*) > 1)"
        )
    )
    bind.execute(
        sa.text(
            "DELETE FROM push_devices WHERE id IN ("
            "SELECT id FROM ("
            "SELECT id, ROW_NUMBER() OVER (PARTITION BY token_hash "
            "ORDER BY updated_at DESC, created_at DESC, id DESC) AS position "
            "FROM push_devices"
            ") ranked WHERE position > 1)"
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "push_devices" not in inspector.get_table_names():
        return
    _revoke_and_deduplicate(bind)
    indexes = {item["name"] for item in inspector.get_indexes("push_devices")}
    if "ux_push_devices_token_hash" not in indexes:
        op.create_index(
            "ux_push_devices_token_hash", "push_devices", ["token_hash"], unique=True
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "push_devices" in inspector.get_table_names():
        indexes = {item["name"] for item in inspector.get_indexes("push_devices")}
        if "ux_push_devices_token_hash" in indexes:
            op.drop_index("ux_push_devices_token_hash", table_name="push_devices")
