"""Initial schema with all tables, device_type field, and query indexes.

Revision ID: 0001
Revises:
Create Date: 2026-03-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.Enum("SUPERADMIN", "ADMIN", "VIEWER", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- groups ---
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- sites ---
    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sites_group_id", "sites", ["group_id"])

    # --- buildings ---
    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("floors", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_buildings_site_id", "buildings", ["site_id"])

    # --- devices ---
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("mac_addr", sa.String(17), nullable=False),
        sa.Column("ip_addr", sa.String(45), nullable=False),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("floor", sa.Integer()),
        sa.Column("protocol", sa.Enum("SSH", "REST", name="deviceprotocol"), nullable=False),
        sa.Column("device_type", sa.String(32), nullable=False, server_default="cisco_ios"),
        sa.Column("ssh_id", sa.String(128)),
        sa.Column("ssh_password_encrypted", sa.Text()),
        sa.Column("ssh_port", sa.Integer(), default=22),
        sa.Column("rest_id", sa.String(128)),
        sa.Column("rest_password_encrypted", sa.Text()),
        sa.Column("rest_port", sa.Integer()),
        sa.Column("status", sa.Enum("UNREGISTERED", "PENDING", "MANAGED", "ERROR", name="devicestatus"),
                  nullable=False, server_default="PENDING"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uptime", sa.String(128)),
        sa.Column("serial_no", sa.String(64)),
        sa.Column("model", sa.String(128)),
        sa.Column("sw_version", sa.String(128)),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Indexes for frequent polling queries
    op.create_index("ix_devices_status", "devices", ["status"])
    op.create_index("ix_devices_consecutive_failures", "devices", ["consecutive_failures"])
    op.create_index("ix_devices_building_id", "devices", ["building_id"])
    op.create_index("ix_devices_site_id", "devices", ["site_id"])

    # --- device_ports ---
    op.create_table(
        "device_ports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("port_name", sa.String(64), nullable=False),
        sa.Column("port_status", sa.String(16)),
        sa.Column("speed", sa.String(32)),
        sa.Column("duplex", sa.String(16)),
        sa.Column("connected_mac", sa.String(17)),
        sa.Column("connected_ip", sa.String(45)),
        sa.Column("vlan_id", sa.String(16)),
        sa.Column("polled_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_device_ports_device_id", "device_ports", ["device_id"])

    # --- vlans ---
    op.create_table(
        "vlans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vlan_id", sa.String(16), nullable=False),
        sa.Column("vlan_name", sa.String(64)),
        sa.Column("polled_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_vlans_device_id", "vlans", ["device_id"])

    # --- endpoints ---
    op.create_table(
        "endpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mac_addr", sa.String(17), nullable=False),
        sa.Column("ip_addr", sa.String(45)),
        sa.Column("port_name", sa.String(64)),
        sa.Column("vlan_id", sa.String(16)),
        sa.Column("polled_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_endpoints_device_id", "endpoints", ["device_id"])

    # --- alarms ---
    op.create_table(
        "alarms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("alarm_type", sa.Enum(
            "DEVICE_DOWN", "DEVICE_UP", "INTERFACE_DOWN", "INTERFACE_UP", "POLL_TIMEOUT",
            name="alarmtype"
        ), nullable=False),
        sa.Column("severity", sa.Enum("CRITICAL", "WARNING", "INFO", name="alarmseverity"), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("status", sa.Enum("OPEN", "ACKNOWLEDGED", "RESOLVED", name="alarmstatus"),
                  nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_alarms_device_id", "alarms", ["device_id"])
    op.create_index("ix_alarms_status", "alarms", ["status"])

    # --- alarm_actions ---
    op.create_table(
        "alarm_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alarm_id", sa.Integer(), sa.ForeignKey("alarms.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alarm_actions_alarm_id", "alarm_actions", ["alarm_id"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64)),
        sa.Column("resource_id", sa.Integer()),
        sa.Column("ip_addr", sa.String(45)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("alarm_actions")
    op.drop_table("alarms")
    op.drop_table("endpoints")
    op.drop_table("vlans")
    op.drop_table("device_ports")
    op.drop_table("devices")
    op.drop_table("buildings")
    op.drop_table("sites")
    op.drop_table("groups")
    op.drop_table("users")
    # Drop enums
    for name in ["userrole", "deviceprotocol", "devicestatus", "alarmtype", "alarmseverity", "alarmstatus"]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
