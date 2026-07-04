#!/usr/bin/env bash
# SnabAgent Backup Script
# Usage: ./scripts/backup.sh [backup_dir]
#
# Backs up:
#   1. PostgreSQL database (pg_dump)
#   2. Redis data (BGSAVE + copy)
#   3. Qdrant snapshots
#   4. Application configuration (.env)

set -euo pipefail

BACKUP_DIR="${1:-./backups/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$BACKUP_DIR"

echo "=== SnabAgent Backup ==="
echo "Destination: $BACKUP_DIR"
echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 1. PostgreSQL
echo ""
echo "--- PostgreSQL ---"
DB_URL="${DATABASE_URL:-postgresql://snabagent:snabagent@localhost:5432/snabagent}"
# Parse components from URL
DB_HOST=$(echo "$DB_URL" | sed -E 's|.*@([^:]+):.*|\1|')
DB_PORT=$(echo "$DB_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_NAME=$(echo "$DB_URL" | sed -E 's|.*/([^?]+).*|\1|')
DB_USER=$(echo "$DB_URL" | sed -E 's|.*://([^:]+):.*|\1|')

PGPASSWORD=$(echo "$DB_URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|') \
  pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=custom --file="$BACKUP_DIR/postgres.dump" 2>/dev/null \
  && echo "  PostgreSQL: OK ($(du -h "$BACKUP_DIR/postgres.dump" | cut -f1))" \
  || echo "  PostgreSQL: SKIPPED (not available)"

# 2. Redis
echo ""
echo "--- Redis ---"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
redis-cli -u "$REDIS_URL" BGSAVE 2>/dev/null \
  && sleep 2 \
  && echo "  Redis: BGSAVE triggered" \
  || echo "  Redis: SKIPPED (not available)"

# 3. Qdrant
echo ""
echo "--- Qdrant ---"
QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
curl -s -X POST "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/snabagent_nsi/snapshots" \
  -o "$BACKUP_DIR/qdrant_snapshot.json" 2>/dev/null \
  && echo "  Qdrant: snapshot created" \
  || echo "  Qdrant: SKIPPED (not available)"

# 4. Config
echo ""
echo "--- Configuration ---"
if [ -f .env ]; then
  cp .env "$BACKUP_DIR/.env.backup"
  echo "  .env: copied"
fi

echo ""
echo "=== Backup Complete ==="
echo "Location: $BACKUP_DIR"
echo "Finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
ls -lah "$BACKUP_DIR/"
