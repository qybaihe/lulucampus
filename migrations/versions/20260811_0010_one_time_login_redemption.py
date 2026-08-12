"""Bind login completion to a one-time initiating-device secret.

Revision ID: 20260811_0010
Revises: 20260811_0009
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0010"
down_revision: str | None = "20260811_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "login_sessions" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("login_sessions")}
    with op.batch_alter_table("login_sessions") as batch:
        if "redemption_token_hash" not in columns:
            batch.add_column(
                sa.Column("redemption_token_hash", sa.String(length=64), nullable=True)
            )
        if "device_install_id_hash" not in columns:
            batch.add_column(
                sa.Column("device_install_id_hash", sa.String(length=64), nullable=True)
            )
        if "redeemed_at" not in columns:
            batch.add_column(sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True))
        if "redemption_operation_hash" not in columns:
            batch.add_column(
                sa.Column("redemption_operation_hash", sa.String(length=64), nullable=True)
            )
        if "redemption_response_ciphertext" not in columns:
            batch.add_column(
                sa.Column("redemption_response_ciphertext", sa.Text(), nullable=True)
            )
    # A pre-migration SUCCESS row has no initiating-device proof. Expiring it
    # avoids turning legacy QR/session identifiers into bearer-token oracles.
    op.execute(
        "UPDATE login_sessions SET status = 'TIMEOUT', error_category = 'SESSION_UPGRADED' "
        "WHERE redemption_token_hash IS NULL AND status IN ('PENDING','WAITING_SCAN','SUCCESS')"
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "login_sessions" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("login_sessions")}
    with op.batch_alter_table("login_sessions") as batch:
        if "redemption_response_ciphertext" in columns:
            batch.drop_column("redemption_response_ciphertext")
        if "redemption_operation_hash" in columns:
            batch.drop_column("redemption_operation_hash")
        if "redeemed_at" in columns:
            batch.drop_column("redeemed_at")
        if "device_install_id_hash" in columns:
            batch.drop_column("device_install_id_hash")
        if "redemption_token_hash" in columns:
            batch.drop_column("redemption_token_hash")
