# SDN Controller

SDN 네트워크 장비 관리 플랫폼 — FastAPI 백엔드 + Vue 3 프론트엔드.

## 아키텍처

```
로컬 개발:  docker-compose (Postgres + Redis + FastAPI + Celery + Vue)
프로덕션:   Fly.io (Backend) + Vercel (Frontend)
```

## 로컬 개발 (docker-compose)

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열고 값 수정:
#   POSTGRES_PASSWORD  — DB 비밀번호 (로컬용 아무 값)
#   MASTER_SECRET      — 32자 이상 랜덤 문자열 (openssl rand -base64 32)
#   SUPERADMIN_PASSWORD — 슈퍼어드민 비밀번호
#   JWT_SECRET         — JWT 서명 키
```

### 2. 실행

```bash
# 최초 실행 시 sdn-lab 네트워크가 compose가 자동 생성함
docker-compose up -d
```

서비스 포트:
| 서비스 | URL |
|--------|-----|
| API    | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

### 3. 가상 장비 (cEOS) 사용 시 추가 설정

cEOS 컨테이너는 `sdn-lab` Docker 네트워크를 공유해야 합니다.
docker-compose가 이 네트워크를 자동 생성하므로 별도 조작 불필요.
단, **Docker-in-Docker가 필요**하므로 로컬 환경에서만 동작합니다.

---

## 프로덕션 배포 (Fly.io + Vercel)

`main` 브랜치에 push하면 GitHub Actions가 자동 배포합니다.

### 최초 설정 (1회만)

#### Fly.io

```bash
brew install flyctl
flyctl auth login

# 앱 생성
flyctl apps create sdn-controller

# Postgres 생성 및 연결
flyctl postgres create --name sdn-controller-db --region nrt
flyctl postgres attach sdn-controller-db --app sdn-controller
# → DATABASE_URL 시크릿이 자동으로 추가되지만 스킴이 postgresql:// (psycopg2)로 설정됨
# → asyncpg를 쓰기 때문에 postgresql+asyncpg:// 스킴으로 덮어써야 함:
flyctl secrets set DATABASE_URL="postgresql+asyncpg://USER:PASS@sdn-controller-db.flycast:5432/sdn_controller"

# Upstash Redis (https://console.upstash.com 에서 생성)
flyctl secrets set \
  CELERY_BROKER_URL="rediss://..." \
  CELERY_RESULT_BACKEND="rediss://..." \
  MASTER_SECRET="$(openssl rand -base64 32)" \
  SUPERADMIN_PASSWORD="your-secure-password" \
  JWT_SECRET="$(openssl rand -base64 32)" \
  CORS_ORIGINS='["https://your-app.vercel.app"]' \
  --app sdn-controller

# 첫 배포
cd backend
flyctl deploy --remote-only
```

#### Vercel

```bash
npm install -g vercel
cd frontend
vercel login
vercel link   # .vercel/project.json 생성

# 환경 변수 설정
vercel env add VITE_API_URL production
# 값: https://sdn-controller.fly.dev
```

#### GitHub Secrets 등록

GitHub repo → Settings → Secrets → Actions:

| Secret | 값 |
|--------|-----|
| `FLY_API_TOKEN` | `flyctl auth token` |
| `VERCEL_TOKEN` | Vercel dashboard → Settings → Tokens |
| `VERCEL_ORG_ID` | `cat frontend/.vercel/project.json \| jq -r .orgId` |
| `VERCEL_PROJECT_ID` | `cat frontend/.vercel/project.json \| jq -r .projectId` |

### 이후 배포

```bash
git push origin main
# → 자동으로: 테스트 → Backend 배포 → Frontend 배포
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Backend API | FastAPI + Python 3.12 |
| DB | PostgreSQL 16 (asyncpg + SQLAlchemy async) |
| Task Queue | Celery + Redis |
| Migrations | Alembic |
| Frontend | Vue 3 + TypeScript + Vite |
| State | Pinia |
| Network Graph | VueFlow |
| Testing | Vitest |
| CI/CD | GitHub Actions |
| Backend Hosting | Fly.io |
| Frontend Hosting | Vercel |

## 관련 문서

- [DEPLOYMENT.md](DEPLOYMENT.md) — 배포 아키텍처 및 DB 충돌 방지 전략 상세
- [frontend/TESTING.md](frontend/TESTING.md) — 프론트엔드 테스트 프레임워크(Vitest) 실행 방법

---

## 주요 알려진 이슈

- **가상 장비 (cEOS)**: `/controller` 화면에서 cEOS 실행은 로컬 환경에서만 가능합니다. Fly.io에서는 Docker-in-Docker 불가.
- **asyncpg SSL**: Fly.io 내부 네트워크(flycast)는 TLS를 지원하지 않습니다. `database.py`와 `alembic/env.py`에서 `connect_args={"ssl": False}`로 처리합니다.
