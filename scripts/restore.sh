#!/usr/bin/env bash
# SnabAgent Restore Script
# Usage: ./scripts/restore.sh <backup_dir>
#
# Restores from:
#   1. PostgreSQL dump (pg_restore)
#   2. Application configuration (.env)

set -euo pipefail

BACKUP_DIR="${1:-}"

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_dir>"
    echo "Example: $0 ./backups/20240101_120000"
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "=== SnabAgent Restore ==="
echo "Source: $BACKUP_DIR"
echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
echo "WARNING: This will OVERWRITE current database!"
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# 1. PostgreSQL
echo ""
echo "--- PostgreSQL ---"
if [ -f "$BACKUP_DIR/postgres.dump" ]; then
    DB_URL="${DATABASE_URL:-postgresql://snabagent:snabagent@localhost:5432/snabagent}"
    DB_HOST=$(echo "$DB_URL" | sed -E 's|.*@([^:]+):.*|\1|')
    DB_PORT=$(echo "$DB_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
    DB_NAME=$(echo "$DB_URL" | sed -E 's|.*/([^?]+).*|\1|')
    DB_USER=$(echo "$DB_URL" | sed -E 's|.*://([^:]+):.*|\1|')
    DB_PASS=$(echo "$DB_URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')

    PGPASSWORD="$DB_PASS" pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -d "$DB_NAME" --clean --if-exists --no-owner \
        "$BACKUP_DIR/postgres.dump" 2>/dev/null \
      && echo "  PostgreSQL: RESTORED" \
      || echo "  PostgreSQL: FAILED (check logs)"
else
    echo "  PostgreSQL: SKIPPED (no postgres.dump found)"
fi

# 2. Config
echo ""
echo "--- Configuration ---"
if [ -f "$BACKUP_DIR/.env.backup" ]; then
    echo "  .env backup available at: $BACKUP_DIR/.env.backup"
    echo "  To restore: cp $BACKUP_DIR/.env.backup .env"
fi

echo ""
echo "=== Restore Complete ==="
echo "Finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
echo "Next steps:"
echo "  1. Restart services: docker compose restart"
echo "  2. Verify health: curl -s http://localhost:8000/health"
