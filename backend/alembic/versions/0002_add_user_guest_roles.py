"""Add USER and GUEST roles to userrole enum.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'USER'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'GUEST'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # Downgrade is a no-op; the values remain but are unused.
    pass
