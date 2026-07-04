# Deployment Guide

## Overview

SnabAgent can be deployed via Docker Compose (recommended for single-node) or Kubernetes with Helm (for HA/production clusters).

## Docker Compose (Recommended)

### Prerequisites
- Docker 24+ and Docker Compose v2
- 4 GB RAM minimum, 8 GB recommended
- Ports: 8000 (API), 8501 (UI), 5432 (PostgreSQL), 6379 (Redis), 6333 (Qdrant)

### Quick Start

```bash
cp .env.example .env
# Edit .env with real values:
#   SECRET_KEY=<random 32+ chars>
#   API_KEY=<random 32+ chars>
#   LLM_PRIMARY=yandexgpt  (or openai)
#   YANDEX_GPT_API_KEY=<key>
#   DATABASE_URL=postgresql+asyncpg://snabagent:snabagent@postgres:5432/snabagent

make dev
make seed-users
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI backend |
| ui | 8501 | Streamlit dashboard |
| postgres | 5432 | PostgreSQL 15 |
| redis | 6379 | Redis 7 (cache + pub/sub) |
| qdrant | 6333 | Qdrant vector DB |
| caddy | 80/443 | Reverse proxy with TLS |

### Environment Variables

See `.env.example` for the full list. Critical variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | JWT signing key (must NOT be "changeme" in prod) |
| `API_KEY` | Yes | Machine-to-machine API key |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `LLM_PRIMARY` | Yes | Primary LLM backend (yandexgpt/openai/fake) |

### Migrations

```bash
# Apply all pending migrations
docker compose exec -T api alembic upgrade head

# Create a new migration
docker compose exec -T api alembic revision --autogenerate -m "description"

# Rollback last migration
docker compose exec -T api alembic downgrade -1
```

### Zero-Downtime Upgrade

1. Pull new images: `docker compose pull`
2. Apply migrations: `docker compose exec -T api alembic upgrade head`
3. Rolling restart: `docker compose up -d --no-deps --build api`
4. Verify health: `curl http://localhost:8000/health/ready`

### Rollback

```bash
# Rollback API to previous version
docker compose up -d --no-deps api  # with previous image tag

# Rollback database
docker compose exec -T api alembic downgrade -1
```

## Kubernetes / Helm

### Prerequisites
- Kubernetes 1.28+
- Helm 3.12+
- cert-manager (for TLS)
- External PostgreSQL, Redis, Qdrant

### Install

```bash
helm install snabagent ./helm/snabagent \
  --set api.image.tag=1.0.0 \
  --set env.SECRET_KEY=<secret> \
  --set env.DATABASE_URL=<postgres_url> \
  --set env.REDIS_URL=<redis_url>
```

### Values

See `helm/snabagent/values.yaml` for all configurable parameters.

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10
```

### SSL/TLS

- **Docker Compose**: Caddy auto-TLS via Let's Encrypt (see `deploy/Caddyfile`)
- **Kubernetes**: cert-manager with ClusterIssuer for Let's Encrypt

## Backup & Restore

```bash
# Backup
./scripts/backup.sh ./backups/$(date +%Y%m%d)

# Restore
./scripts/restore.sh ./backups/20260604
```

See `scripts/backup.sh` and `scripts/restore.sh` for details.
