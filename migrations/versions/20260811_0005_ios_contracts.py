"""Complete contracts required by the native iOS client.

Revision ID: 20260811_0005
Revises: 20260811_0004
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0005"
down_revision: str | None = "20260811_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, name: str) -> bool:
    if not _has_table(table):
        return False
    return any(column["name"] == name for column in sa.inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if not _has_column("users", "notification_preferences"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "notification_preferences",
                    sa.JSON(),
                    nullable=False,
                    server_default=sa.text("'{}'"),
                )
            )
    if not _has_column("trust_appeals", "result"):
        with op.batch_alter_table("trust_appeals") as batch_op:
            batch_op.add_column(sa.Column("result", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_table("media_assets"):
        op.create_table(
            "media_assets",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("owner_user_id", sa.String(length=36), nullable=False),
            sa.Column("content_type", sa.String(length=64), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("storage_path", sa.Text(), nullable=False),
            sa.Column("byte_count", sa.Integer(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_media_assets_owner_user_id", "media_assets", ["owner_user_id"])
        op.create_index("ix_media_assets_sha256", "media_assets", ["sha256"])
    if not _has_table("media_channel_grants"):
        op.create_table(
            "media_channel_grants",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("media_id", sa.String(length=36), nullable=False),
            sa.Column("channel_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["media_id"], ["media_assets.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("media_id", "channel_id"),
        )
        op.create_index(
            "ix_media_channel_grants_channel_id", "media_channel_grants", ["channel_id"]
        )
        op.create_index(
            "ix_media_channel_grants_media_id", "media_channel_grants", ["media_id"]
        )


def downgrade() -> None:
    if _has_table("media_channel_grants"):
        op.drop_index("ix_media_channel_grants_media_id", table_name="media_channel_grants")
        op.drop_index("ix_media_channel_grants_channel_id", table_name="media_channel_grants")
        op.drop_table("media_channel_grants")
    if _has_table("media_assets"):
        op.drop_index("ix_media_assets_sha256", table_name="media_assets")
        op.drop_index("ix_media_assets_owner_user_id", table_name="media_assets")
        op.drop_table("media_assets")
    if _has_column("trust_appeals", "result"):
        with op.batch_alter_table("trust_appeals") as batch_op:
            batch_op.drop_column("decided_at")
            batch_op.drop_column("result")
    if _has_column("users", "notification_preferences"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("notification_preferences")
