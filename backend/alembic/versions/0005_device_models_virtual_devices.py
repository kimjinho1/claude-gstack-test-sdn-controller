"""device_models and virtual_devices tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "device_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("vendor", sa.String(64), nullable=False),
        sa.Column("device_type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("docker_image", sa.String(128), nullable=True),
        sa.Column("is_virtual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "virtual_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("container_id", sa.String(128), nullable=True),
        sa.Column("ssh_port", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="starting"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["model_id"], ["device_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_virtual_devices_model_id", "virtual_devices", ["model_id"])


def downgrade():
    op.drop_index("ix_virtual_devices_model_id", table_name="virtual_devices")
    op.drop_table("virtual_devices")
    op.drop_table("device_models")
