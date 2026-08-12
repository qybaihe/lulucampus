"""Store encrypted APNs tokens and provider delivery outcomes.

Revision ID: 20260811_0009
Revises: 20260811_0008
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0009"
down_revision: str | None = "20260811_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "push_devices" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("push_devices")}
        with op.batch_alter_table("push_devices") as batch:
            if "token_ciphertext" not in columns:
                batch.add_column(sa.Column("token_ciphertext", sa.Text(), nullable=True))
            if "token_key_id" not in columns:
                batch.add_column(sa.Column("token_key_id", sa.String(length=64), nullable=True))
        # Hash-only legacy rows cannot be delivered safely. They are reactivated
        # by the next explicit registration, which supplies a fresh token.
        op.execute("UPDATE push_devices SET active = false WHERE token_ciphertext IS NULL")

    inspector = sa.inspect(op.get_bind())
    if "push_deliveries" not in inspector.get_table_names():
        op.create_table(
            "push_deliveries",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("notification_id", sa.String(length=36), nullable=False),
            sa.Column("device_id", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("provider_status", sa.Integer(), nullable=True),
            sa.Column("provider_reason", sa.String(length=128), nullable=True),
            sa.Column("provider_message_id", sa.String(length=128), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["notification_id"], ["notifications.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["device_id"], ["push_devices.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_push_deliveries_notification_id", "push_deliveries", ["notification_id"]
        )
        op.create_index("ix_push_deliveries_device_id", "push_deliveries", ["device_id"])
        op.create_index("ix_push_deliveries_status", "push_deliveries", ["status"])
        op.create_index(
            "ix_push_deliveries_next_attempt_at",
            "push_deliveries",
            ["next_attempt_at"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "push_deliveries" in inspector.get_table_names():
        op.drop_table("push_deliveries")
    if "push_devices" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("push_devices")}
        with op.batch_alter_table("push_devices") as batch:
            if "token_key_id" in columns:
                batch.drop_column("token_key_id")
            if "token_ciphertext" in columns:
                batch.drop_column("token_ciphertext")
