"""device_links table

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "device_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "child_id", name="uq_device_link"),
    )
    op.create_index("ix_device_links_parent_id", "device_links", ["parent_id"])
    op.create_index("ix_device_links_child_id", "device_links", ["child_id"])


def downgrade():
    op.drop_index("ix_device_links_child_id", table_name="device_links")
    op.drop_index("ix_device_links_parent_id", table_name="device_links")
    op.drop_table("device_links")
