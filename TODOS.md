# TODOS

## TODO-1: INTERFACE_DOWN/UP 알람 감지 로직

**What:** `alarm_check.py`에 포트 상태 변화(UP→DOWN, DOWN→UP) 감지 및 알람 생성 추가

**Why:** `AlarmType.INTERFACE_DOWN/UP` ENUM이 이미 정의되어 있지만 detection 로직이 없다.
포트가 다운되어도 DEVICE_DOWN이 발생하지 않으면 운영자가 모른다. 특히 업링크 포트 다운
같은 심각한 이벤트를 사전 감지할 수 없어 장애 대응이 늦어진다.

**Pros:** 디바이스 다운 전에 포트 다운으로 사전 감지 가능. DEVICE_DOWN보다 세밀한 알람 제공.

**Cons:** 이전 폴링 스냅샷과 현재 스냅샷 비교 로직 필요.
device_ports에 이전 상태를 보관하거나 별도 컬럼(previous_status) 추가 필요.

**Context:** 현재 `_check_device_alarms()`는 `consecutive_failures >= 3`만 체크한다.
포트 상태 변화 감지를 하려면 폴링 사이클마다 이전 port_status 값과 비교해야 하므로
device_ports 스키마 변경 + 마이그레이션 필요. Phase 2 (device_ports 안정화 후) 타이밍이 적절.

**Depends on / blocked by:** Phase 2 device_ports 완료 후

---

## TODO-2: AuditLog 적용 범위 확대

**What:** `audit()` 함수를 auth.py 이외의 API (devices, topology, alarms)에도 적용

**Why:** Phase 1 설계에는 "자격증명 조회 + 주요 액션 기록"이 필수로 포함되어 있었으나,
현재는 `/auth/login`과 `/auth/change-password`에만 기록된다.
장비 등록/삭제, 알람 조치, 자격증명 복호화 이벤트가 감사 추적되지 않아
컴플라이언스/보안 요구사항(교육청 납품 시 필수)을 충족하지 못한다.

**Pros:** 보안 감사 추적 완성. 누가 언제 어떤 장비를 등록/삭제했는지 추적 가능.

**Cons:** API 함수마다 `await audit(db, user, action, ...)` 한 줄 추가 필요.
현재 `audit()` 함수는 이미 완성되어 있어 추가 비용 최소.

**Context:** `deps.py`의 `audit()` 함수는 완성된 상태. 호출만 추가하면 된다.
우선순위: `POST /devices` (자격증명 저장), `DELETE /devices/{id}`, `POST /alarms/{id}/actions`.

**Depends on / blocked by:** 없음 (언제든 추가 가능)

---

## TODO-3: Celery 워커 실패 알림 체인

**What:** Celery 태스크 실패 시 알림 체인 구축 (Sentry / 로그 파일 집계 / 웹훅)

**Why:** 현재 Celery 태스크가 예외로 종료되면 `logger.warning()`만 출력된다.
프로덕션에서 폴링 워커 전체가 조용히 멈추거나 Redis 연결이 끊겨도 운영자가 모른다.
장비 관리 플랫폼에서 폴링이 멈추는 것은 서비스 중단과 동일하다.

**Pros:** 폴링 중단 조기 감지. 온콜 알림으로 즉각 대응 가능.

**Cons:** Sentry 또는 외부 웹훅 서비스 의존 추가. 설정 복잡도 소폭 증가.

**Context:** Celery `task_failure_signal`로 실패 훅 등록 가능.
로컬 디버깅 시 `task_always_eager=True`로 즉시 실행 가능.
Phase 3 (운영 안정화 후) 우선순위.

**Depends on / blocked by:** Phase 3 이후 (운영 배포 경험 쌓인 후)

---

## TODO-4: API 페이지네이션 (list_devices / list_alarms)

**What:** `GET /devices` 및 `GET /alarms`에 `limit` / `offset` 쿼리 파라미터 추가

**Why:** 현재 모든 레코드를 한 번에 반환한다. 장비 100대 이상, 알람 이력 수천 건이 쌓이면
단일 응답이 수십 MB가 되어 응답 지연 및 메모리 문제 발생 가능.

**Pros:** 응답 크기 제어, 프론트엔드 infinite scroll / 페이지 UI 지원.

**Cons:** 프론트엔드 스토어(Pinia)에서 페이지 상태 관리 추가 필요.

**Context:** FastAPI에서는 `skip: int = 0, limit: int = 100` 파라미터로 즉시 구현 가능.
MVP 배포 전 (장비 100대 초과 운영 환경) 적용 권장.

**Depends on / blocked by:** 없음

---

## TODO-5: 동시 알람 생성 중복 방지 (DEVICE_DOWN 중복)

**What:** 동시에 실행된 두 개의 `check_all_devices` 태스크가 같은 장비에 대해 DEVICE_DOWN 알람을 중복 생성하는 race condition 방지

**Why:** 현재 코드는 open DEVICE_DOWN 존재 여부를 SELECT 후 없으면 INSERT한다.
두 태스크가 동시에 SELECT → 둘 다 없음 확인 → 둘 다 INSERT하면 같은 장비에 중복 알람 발생.
Celery beat 지연 + 재시도 환경에서 현실적으로 발생 가능.

**Pros:** 알람 이력 오염 방지. 운영자가 중복 알람으로 혼란 겪지 않음.

**Cons:** `(device_id, alarm_type, status=OPEN)` 유니크 제약은 enum 값 포함 복합 조건이라 DB 제약으로 구현하기 까다로움. 애플리케이션 레벨에서 `IntegrityError` catch 패턴 또는 Celery 단일 워커 제한으로 우회 가능.

**Context:** 현재 Celery beat는 1분 주기로 check_all_devices를 실행.
워커가 1개면 문제 없지만 워커 2개 이상 운영 시 발생 가능.
단기 해결: alarm_check 태스크는 `@celery_app.task(..., acks_late=True)` + `CELERYD_PREFETCH_MULTIPLIER=1`로 직렬화.

**Depends on / blocked by:** 워커 수평 확장 시점 (현재 단일 워커면 낮은 우선순위)

---

## TODO-6: device-links API RBAC 적용

**What:** `POST /device-links` 및 `DELETE /device-links/{id}` 엔드포인트에 역할 기반 접근 제어(RBAC) 추가

**Why:** 현재 인증된 모든 사용자(VIEWER 포함)가 토폴로지 링크를 생성/삭제할 수 있다.
SDN 컨텍스트에서 링크는 논리 네트워크 토폴로지를 의미하므로, 읽기 전용 운영자가 임의로 변경하면 실제 네트워크 구성을 잘못 표현할 수 있다.

**Pros:** VIEWER는 조회만, ADMIN 이상만 생성/삭제 가능 — 의도치 않은 토폴로지 변경 방지.

**Cons:** `require_admin` 의존성 하나 추가하면 충분. 추가 비용 최소.

**Context:** `backend/app/api/deps.py`에 `require_admin` 의존성이 이미 있다. `GET /device-links/graph` 및 `GET /device-links`는 모든 인증 사용자에게 허용 유지. `POST`/`DELETE`에만 `require_admin` 적용.
adversarial review (v0.1.3.0 shipping)에서 발견됨.

**Depends on / blocked by:** 없음
