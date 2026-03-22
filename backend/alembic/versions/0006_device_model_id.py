"""add model_id FK to devices

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("model_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_devices_model_id",
        "devices",
        "device_models",
        ["model_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_devices_model_id", "devices", ["model_id"])


def downgrade() -> None:
    op.drop_index("ix_devices_model_id", table_name="devices")
    op.drop_constraint("fk_devices_model_id", "devices", type_="foreignkey")
    op.drop_column("devices", "model_id")
