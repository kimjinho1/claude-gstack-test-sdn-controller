# Changelog

All notable changes to the SDN Controller project will be documented in this file.

## [0.1.1.0] - 2026-03-22

### Added
- User management API (`/users` CRUD) with role hierarchy enforcement — actors can only manage users with strictly lower role level (SUPERADMIN > ADMIN > USER > GUEST)
- `UserRole.USER` and `UserRole.GUEST` roles replacing the former `VIEWER` role; `level()` method enables programmatic role comparison
- Alembic migration 0002: adds `USER` and `GUEST` values to the `userrole` PostgreSQL enum
- Sidebar navigation tabs in `DashboardLayout`: 사용자 관리 (admin-only), 그룹 관리 (admin-only), 장비 관리
- Topology tree inline rename (✎) and delete (✕) buttons with hover-reveal — group, site, and building nodes
- Bulk-delete endpoints for groups, sites, buildings, devices, and users
- Frontend `userManage` Pinia store with `fetchUsers`, `createUser`, `updateUser`, `deleteUser`, `bulkDelete`
- `UsersView.vue`: user list table with search, role filter, create/edit modal, bulk delete
- `GroupManageView.vue`: flat group/site/building table with inline edit and add modal

### Changed
- `auth.ts` store: added `ROLE_LEVEL`, `ROLE_LABEL`, `isSuperAdmin`, `roleLevel` computed; updated `UserRole` type to include `USER` and `GUEST`
- `DevicesView.vue`: added search filter, checkbox bulk selection, and bulk delete
- Topology tree conditionally rendered only on `/devices` routes
- Active nav-item highlight uses `route.path.startsWith()` for sub-route matching
- `devices.py` bulk-delete endpoint: typed with `BulkDeleteRequest` Pydantic model (was untyped `dict`)

### Fixed
- `conftest.py`: updated test fixture from removed `UserRole.VIEWER` to `UserRole.USER`
- `test_register_device_invalid_mac`: updated to match MAC normalization behavior (`AABBCCDDEEFF` → 201 with normalized value; non-hex `ZZZZZZZZZZZZ` → 422)

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
