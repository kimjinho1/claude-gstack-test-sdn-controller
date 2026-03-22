# Changelog

All notable changes to the SDN Controller project will be documented in this file.

## [0.1.0.0] - 2026-03-22

### Added
- FastAPI backend with JWT authentication (SUPERADMIN / ADMIN / VIEWER roles)
- Group → Site → Building topology CRUD API
- Device registration and management (SSH/REST protocols, multi-vendor device_type support)
- Fernet-encrypted credential storage (MASTER_SECRET env var, startup validation for default values)
- Celery + Redis async device polling (module-level engine singleton, try/finally SSH cleanup)
- Device status state machine: PENDING → MANAGED → ERROR with automatic Celery polling
- Alarm system: DEVICE_DOWN (3 consecutive failures), DEVICE_UP (OPEN recovery events)
- Alarm acknowledge and action endpoints (ADMIN-only RBAC)
- Audit logging for all critical actions in the same transaction as the action
- Alembic migrations with performance indexes on devices, alarms, ports, vlans, endpoints
- IPv4 address validation and device_type allowlist (cisco_ios / cisco_xe / cisco_nxos) on device create
- Per-device exception isolation in alarm_check task (single device failure does not stop alarm loop)
- Docker Compose single-command deployment (PostgreSQL + Redis + backend + Celery worker + Vue frontend)
- Vue 3 + Vite + Pinia frontend with Group/Site/Building topology tree, device list, alarm panel
- 31 passing tests across auth, device state machine, alarm logic, API integration, and security
