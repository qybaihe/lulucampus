"""Create taste import sessions and taste profiles.

Revision ID: 20260811_0002
Revises: 20260811_0001
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op

from onemore.core.database import Base
from onemore.db.models import TasteImportSession, TasteProfile  # noqa: F401

revision: str = "20260811_0002"
down_revision: str | None = "20260811_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[TasteImportSession.__table__, TasteProfile.__table__],
        checkfirst=True,
    )


def downgrade() -> None:
    Base.metadata.drop_all(
        bind=op.get_bind(),
        tables=[TasteImportSession.__table__, TasteProfile.__table__],
        checkfirst=True,
    )
