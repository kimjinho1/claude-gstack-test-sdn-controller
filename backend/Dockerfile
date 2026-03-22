FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Docker CLI binary — pre-downloaded to bin/docker (avoids slow curl on every build)
COPY bin/docker /usr/local/bin/docker
RUN chmod +x /usr/local/bin/docker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
