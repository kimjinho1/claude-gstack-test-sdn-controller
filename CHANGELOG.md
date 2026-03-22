# Changelog

All notable changes to the SDN Controller project will be documented in this file.

## [0.1.7.0] - 2026-03-23

### Added
- **관제/설정 화면 분리** — 장비 관제(`/devices`)와 컨트롤러 설정(`/settings`)이 별도 페이지로 분리됩니다. 장비 목록 클릭 시 사이드 드로어가 열려 실시간 포트·VLAN·알람 현황을 확인할 수 있습니다.
- **드로어 패널 리사이즈** — 관제 드로어의 왼쪽 가장자리를 드래그해 너비를 조정할 수 있습니다 (380px – 1200px).
- **포트 툴팁** — 포트 맵에서 포트 위에 마우스를 올리면 속도·VLAN·연결 상태 상세 정보가 툴팁으로 표시됩니다.
- **Vitest 테스트 프레임워크** — 프론트엔드에 Vitest + @vue/test-utils + jsdom 테스트 인프라가 추가됩니다. `npm test`로 실행.
- **포트명 약어·BPS 포맷 단위 테스트** — `shortName` 및 `formatBps` 유틸리티 함수에 대한 14개 테스트 추가.

### Fixed
- **자격증명 API 노출 방지** — SSH 연결 실패 시 Netmiko 예외 메시지(호스트명·비밀번호 포함 가능)가 HTTP 응답에 직접 노출되던 문제를 수정. 실제 에러는 서버 로그에만 기록합니다.
- **device_type 허용 목록** — DB에서 읽은 `device_type`을 검증 없이 Netmiko에 전달하던 문제 수정. `cisco_ios`, `arista_eos`, `huawei_vrp` 등 허용된 값만 사용합니다.
- **trigger_poll 권한 강화** — 일반 사용자도 폴링을 강제 실행할 수 있던 엔드포인트를 관리자 전용(`require_admin`)으로 변경.
- **openMonitor 레이스 컨디션** — 장비를 빠르게 전환할 때 이전 장비의 포트·VLAN 데이터가 새 패널에 표시되던 문제 수정. 세대(generation) 카운터로 오래된 응답을 무시합니다.
- **Huawei 포트 regex 오류** — `(up|down|*)` 패턴의 `*`가 이스케이프되지 않아 `re.error`가 발생하던 문제 수정.
- **VLAN 이름 파싱 오류** — Huawei `_parse_vlans_huawei`에서 `re.DOTALL` 플래그로 인해 VLAN 이름이 여러 항목에 걸쳐 잘못 파싱되던 문제 수정.
- **get_running_config StopIteration 방지** — CLI 에러 파싱에서 `next()`에 기본값을 추가해 예외 전파 방지.
- **폴링 미관리 장비 차단** — MANAGED 상태가 아닌 장비에 폴링 태스크가 큐에 등록되지 않도록 가드 추가.
- **드래그 이벤트 리스너 누수 방지** — DrawerPanel이 드래그 도중 언마운트될 때 `mousemove`·`mouseup` 리스너가 정리되지 않던 문제 수정.
- **장비 전환 시 loadingConfig 초기화** — 다른 장비 클릭 시 "가져오는 중..." 버튼이 stuck 상태로 남아있던 문제 수정.
- **포커스 아웃라인 접근성** — 검색 입력창과 필터 셀렉트에서 `outline: none`이 포커스 표시를 완전히 제거하던 문제 수정.

## [0.1.6.0] - 2026-03-22

### Added
- **가상 장비 컨테이너 IP** — after launching a virtual device container, the UI now shows the container's direct IP on the `sdn-lab` Docker network. Register devices with `container_ip:22` (not `localhost:<ssh_port>`) so Celery workers can connect directly without host-port mapping.
- **Mock Arista cEOS SSH server** (`docker/mock-ceos/`) — lightweight Python paramiko server that responds to Arista EOS CLI commands (show version, show interfaces, show vlan, show mac address-table). Replaces the real cEOS-lab image for lab testing without a license.
- **Docker-in-Docker worker** — `docker-compose.yml` now mounts the host Docker socket into the backend/worker container so the API can launch virtual device containers from inside the stack.
- **Port traffic BPS calculation** — device polling now computes `traffic_in_bps` and `traffic_out_bps` from byte counter deltas between polls. Handles counter wrap/reset gracefully.

### Fixed
- **Arista EOS `show version` parsing** — SSH driver now correctly parses `Software image version: X.Y.ZF`, `Uptime: N weeks, N days`, and `Serial number: JPEXXX` formats. Previously these fields were missed and devices stayed in PENDING status.
- **TextFSM partial results** — when TextFSM returns some fields but not all required fields, the driver now falls back to regex parsing on raw text instead of returning incomplete SystemInfo.
- **Worker SSH connection failure** — worker was connecting to `container_ip:2222` (host-mapped port) instead of `container_ip:22` (direct container port). Fixed by storing `container_ip` from docker inspect and displaying it in the UI as the correct address to use.

## [0.1.5.0] - 2026-03-22

### Added
- **컨트롤러 설정 (Controller Settings)** — new admin-only nav section with two sub-tabs:
  - **장비 모델 (Device Models)**: catalog of physical/virtual device types with full CRUD. Includes name, vendor, device_type, description, docker_image, and image_url fields. Pre-seeded with Arista cEOS-lab model on startup.
  - **가상 장비 (Virtual Devices)**: launch and manage Arista cEOS Docker containers for lab testing directly from the UI. Each container maps a configurable SSH port (1024–65535). Status syncs live from Docker on every list fetch.
- **Alembic migration 0005**: `device_models` and `virtual_devices` tables with proper FK and index on `model_id`.
- **`arista_eos` SSH driver support**: added to `SSH_DEVICE_TYPES` allowlist and Netmiko device map; regex fallback parser now handles Arista `show version` format alongside Cisco IOS patterns.

### Fixed
- SSH driver `model` field now falls back to `d.get("model", "")` when NAPALM returns hardware as a non-list — prevents empty model on some Arista responses.
- Regex fallback parser for SSH driver now captures both Cisco and Arista serial number/model/version patterns.

## [0.1.4.0] - 2026-03-22

### Added
- **Dark/Light theme system** (`theme.css`, `theme.ts`): CSS custom properties for all semantic colors (`--bg-base`, `--text-primary`, `--accent-primary`, etc.) with dark (default) and light variants. Controlled via `[data-theme]` on `<html>`.
- **Theme Pinia store** (`stores/theme.ts`): persists preference to `localStorage`, safe for private browsing and SSR environments.
- **Theme toggle button** in topbar: `☀️`/`🌙` switches themes live without page reload.
- **Collapsible sidebar**: hamburger `☰` button toggles sidebar with smooth max-width + opacity animation.
- **FOUC prevention**: synchronous `<script>` in `index.html` applies saved theme before Vue mounts — eliminates dark-to-light flash for light-mode users.

### Changed
- Every view and component now uses CSS custom properties instead of hardcoded colors — future theme additions require only a single CSS block, not touching every component.
- Group tree panel `🌲` is now accessible from all routes (previously topology-only).
- Topology canvas background dot grid adapts to the active theme.

### Fixed
- `GroupManageView`, `UsersView`, `AlarmsView`: text was invisible in dark mode due to hardcoded white/light background colors — replaced with CSS vars throughout.
- Hardcoded `#ff6b6b` color in critical alarm badge, topology error banner, and dashboard alarm badge replaced with `var(--danger)` for theme consistency.
- `.device-node:hover` box-shadow and status dot glow shadows converted to `color-mix()` with semantic CSS vars — no longer drift when theme variables are updated.
- `RegisterDeviceModal` section divider now uses `--border-subtle` (was inconsistently `--border-color`).
- Sidebar and tree-panel `<Transition>` animations fixed: `width` → `max-width` transition which correctly works with Vue's `v-show`.

## [0.1.3.0] - 2026-03-22

### Added
- **Network Topology View** (`TopologyView.vue`): interactive VueFlow canvas displaying all devices as nodes with dagre tree layout (TB direction). Node colors reflect device status (MANAGED=green, ERROR=red, PENDING=orange, UNREGISTERED=gray). Minimap, zoom controls, and fit-to-view button included.
- **DeviceNode component** (`DeviceNode.vue`): custom VueFlow node rendering device name, IP, status badge, protocol badge, and connection Handles.
- **Device link management**: topology edges can be created by dragging from node handles or via the "+ 링크 추가" modal. Selected edges show an action bar for deletion.
- **`DeviceLink` model** (`backend/app/models/device.py`): `device_links` table with `parent_id`/`child_id` FKs (CASCADE DELETE), `UniqueConstraint("parent_id", "child_id")`, and indexed columns.
- **Alembic migration 0004**: creates the `device_links` table with indexes.
- **Device Links API** (`backend/app/api/device_links.py`): `GET /device-links/graph` (combined devices + links for topology), `GET /device-links` (list), `POST /device-links` (create with self-loop and duplicate validation), `DELETE /device-links/{id}`.
- **Parent device selector in DevicesView**: device edit drawer includes "상위 장비 (부모)" select — automatically creates/deletes device links when saving.
- **Test coverage**: 9 integration tests for all device-links API endpoints including edge cases (self-loop, missing device, duplicate, concurrent create with IntegrityError).

### Changed
- `DashboardLayout.vue`: applied full Palantir dark theme (`#111820` topbar, `#0e1520` sidebar/content, `#131f2b` drawer, `#1e2d3a` borders, `#1d6fa4` active nav); added 토폴로지 nav item; `content.no-pad` class for full-bleed views.
- `DrawerPanel.vue`: dark theme CSS (was light Blueprint theme).
- Default route `/` now redirects to `/topology` (was `/devices` due to a duplicate redirect entry bug).
- `DevicesView.vue`: dark Palantir theme; parent device selector added to edit drawer.

### Fixed
- Router: removed duplicate `{ path: "", redirect: "/devices" }` entry that shadowed the `/topology` redirect (Vue Router first-match rule).
- `device_links` `create_link`: wrapped DB insert in `IntegrityError` handler to return 409 instead of 500 on concurrent duplicate inserts.
- `DevicesView.openEdit`: link fetch failure now surfaces an error instead of silently leaving `parent_id` as `null`.
- `DevicesView.submitEdit`: eliminated redundant link list re-fetch — uses `_originalParentId` snapshot from `openEdit` for change detection; 404 on `DELETE` (already-deleted link) is tolerated.
- `TopologyView.deleteEdge`: failure no longer causes optimistic edge removal — edge stays in place and error banner is shown.
- `TopologyView.createLink`: only swallows 409 (duplicate); other errors are re-thrown to surface in the modal.
- `TopologyView.applyLayout`: guards against empty node list to prevent dagre producing NaN positions.

## [0.1.2.0] - 2026-03-22

### Added
- `user_group_access` association table (Alembic migration 0003): many-to-many relationship between users and groups for per-user group access restriction
- User group assignment API: `GET /users/{id}/groups` (returns accessible group IDs) and `PUT /users/{id}/groups` (sets accessible groups; empty list = all groups)
- Group access selector in `UsersView.vue`: ADMIN/USER/GUEST users can be restricted to specific groups via multi-select in the edit drawer

### Changed
- `DevicesView.vue`: device click now opens an editable drawer (was read-only detail) — editable fields: name, floor, SSH credentials (ssh_id, ssh_password, ssh_port) or REST credentials by protocol; PATCH /devices/{id} on save; password fields only sent if non-empty
- `GroupManageView.vue` building parent selector: replaced cascading group→site selector with a flat "GroupName / SiteName" single select (no intermediate group selection required)
- Applied Palantir/Blueprint.js-inspired UI style across all management views (`UsersView.vue`, `GroupManageView.vue`, `DevicesView.vue`): #1d6fa4 primary blue, #182026 dark text, #5c7080 muted, #dce1e7 borders, 2px border-radius, uppercase table headers

### Fixed
- `accessible_groups` relationship: added `uselist=True` and `lazy="selectin"` to prevent `None` return when no groups are assigned (was causing 500 on `GET /users/{id}/groups`)
- Added `or []` guard in `get_user_groups` endpoint to handle edge case of `None` accessible_groups

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
