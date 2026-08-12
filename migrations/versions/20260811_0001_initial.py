"""Create the complete ONE MORE V2.1 schema.

Revision ID: 20260811_0001
Revises: None
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op

from onemore.core.database import Base
from onemore.db import models  # noqa: F401

revision: str = "20260811_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
