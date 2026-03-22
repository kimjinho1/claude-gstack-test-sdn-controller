# Deployment Guide

## 아키텍처

```
GitHub push → main
    ├── Fly.io (Backend)
    │   ├── release_command: alembic upgrade head  ← DB 충돌 방지 핵심
    │   ├── app process:    uvicorn (FastAPI)
    │   ├── worker process: celery worker
    │   └── beat process:   celery beat
    │
    └── Vercel (Frontend)
        └── Vue 3 SPA (VITE_API_URL → Fly.io)
```

## 왜 DB 충돌이 났었나?

`docker-compose.yml`의 startup command에 `alembic upgrade head`가 포함되어 있으면:
- 여러 컨테이너(api, worker, beat)가 **동시에** migration을 실행
- 새 배포 중 이전/신규 인스턴스가 **동시에** migration을 시도

**해결**: `fly.toml`의 `[deploy] release_command`는:
1. 이전 인스턴스가 트래픽 처리 중
2. 새 이미지로 migration **한 번만** 실행 (Alembic 내부 lock 보장)
3. 성공 후 → 새 인스턴스 시작
4. 이전 인스턴스 종료

---

## 최초 설정 (1회만)

### 1. Fly.io 초기화

```bash
# Fly CLI 설치
brew install flyctl
flyctl auth login

# 앱 생성 (fly.toml의 app 이름과 일치해야 함)
flyctl apps create sdn-controller

# Fly Postgres 생성
flyctl postgres create --name sdn-controller-db --region nrt
flyctl postgres attach sdn-controller-db --app sdn-controller
# → DATABASE_URL이 자동으로 secrets에 추가됨

# Upstash Redis (무료 플랜 사용 권장)
# https://console.upstash.com 에서 Redis 생성 후 URL 복사

# Secrets 설정
flyctl secrets set \
  CELERY_BROKER_URL="rediss://..." \
  CELERY_RESULT_BACKEND="rediss://..." \
  MASTER_SECRET="$(openssl rand -base64 32)" \
  SUPERADMIN_PASSWORD="your-secure-password" \
  JWT_SECRET="$(openssl rand -base64 32)" \
  CORS_ORIGINS='["https://your-app.vercel.app"]' \
  --app sdn-controller
```

### 2. Vercel 초기화

```bash
npm install -g vercel
cd frontend
vercel login
vercel link   # 프로젝트 연결 후 .vercel/project.json 생성됨

# Vercel 환경 변수 설정
vercel env add VITE_API_URL production
# 값: https://sdn-controller.fly.dev
```

### 3. GitHub Secrets 등록

GitHub repo → Settings → Secrets → Actions에 다음 추가:

| Secret | 값 |
|--------|-----|
| `FLY_API_TOKEN` | `flyctl auth token` 출력값 |
| `VERCEL_TOKEN` | Vercel dashboard → Settings → Tokens |
| `VERCEL_ORG_ID` | `cat frontend/.vercel/project.json \| jq -r .orgId` |
| `VERCEL_PROJECT_ID` | `cat frontend/.vercel/project.json \| jq -r .projectId` |

### 4. 첫 배포

```bash
# main에 push하면 GitHub Actions가 자동 배포
git push origin main
```

---

## 이후 배포

`main` 브랜치에 push하면 자동으로:
1. Vitest 테스트 실행
2. 테스트 통과 시 Backend 배포 (alembic upgrade head → uvicorn 기동)
3. Backend 배포 성공 시 Frontend 배포 (Vercel)
   - Backend 실패 시 Frontend 배포는 건너뜀 (broken API 방지)

---

## 로컬 개발

로컬 개발은 기존 docker-compose 그대로:

```bash
cp .env.example .env  # 환경변수 설정
docker-compose up -d
```

---

## 주의사항

- **가상 장비 기능** (`/controller` 화면의 cEOS 실행)은 Fly.io에서 비활성화됨
  - `/var/run/docker.sock`이 없어 Docker-in-Docker 불가
  - 로컬 개발 환경에서만 사용 가능
