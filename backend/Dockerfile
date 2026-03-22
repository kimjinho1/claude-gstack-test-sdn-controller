FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Docker CLI binary — 가상 장비 실행용 (local dev + 로컬 Docker 환경 전용)
# Fly.io 배포 시에도 포함되지만 /var/run/docker.sock 미존재로 가상 장비 기능만 비활성화됨
COPY bin/docker /usr/local/bin/docker
RUN chmod +x /usr/local/bin/docker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
