"""partial unique index on virtual_devices.ssh_port for active devices

Revision ID: 0007
Revises: 9b7dc8d8b529
Create Date: 2026-03-23
"""

from alembic import op

revision = "0007"
down_revision = "9b7dc8d8b529"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Partial unique index: only one active virtual device may hold each ssh_port.
    # Stopped devices are excluded so the port can be reused after stopping.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_virtual_devices_ssh_port_active
        ON virtual_devices (ssh_port)
        WHERE status != 'stopped'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_virtual_devices_ssh_port_active")
