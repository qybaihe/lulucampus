"""Persist and replay authenticated write responses by idempotency key.

Revision ID: 20260811_0007
Revises: 20260811_0006
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0007"
down_revision: str | None = "20260811_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "idempotency_records" in inspector.get_table_names():
        return
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("method", sa.String(length=8), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column(
            "response_content_type",
            sa.String(length=128),
            nullable=False,
            server_default="application/json",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "method", "path", "idempotency_key"),
    )
    op.create_index("ix_idempotency_records_user_id", "idempotency_records", ["user_id"])
    op.create_index(
        "ix_idempotency_records_expires_at", "idempotency_records", ["expires_at"]
    )


def downgrade() -> None:
    if "idempotency_records" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("idempotency_records")
