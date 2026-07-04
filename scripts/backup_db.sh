#!/usr/bin/env bash
# Database backup utility for Mandate.
#
# - SQLite (default/dev): copies the DB file using the online `.backup` API so a
#   consistent snapshot is taken even while the API is serving requests.
# - Postgres (production): runs `pg_dump` against MANDATE_DATABASE_URL.
#
# Backups are timestamped and written to ./backups (override with BACKUP_DIR).
# Old backups beyond RETENTION (default 14) are pruned. Schedule via cron, e.g.
#   0 * * * * /app/scripts/backup_db.sh   # hourly
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
RETENTION="${RETENTION:-14}"
DB_URL="${MANDATE_DATABASE_URL:-sqlite:///./data/mandate.db}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [[ "$DB_URL" == sqlite* ]]; then
  SRC="${DB_URL#sqlite:///}"
  # Resolve relative paths against the backend directory (where the app runs).
  [[ "$SRC" = /* ]] || SRC="$ROOT/backend/$SRC"
  DEST="$BACKUP_DIR/mandate-$STAMP.db"
  if [[ ! -f "$SRC" ]]; then
    echo "error: sqlite database not found at $SRC" >&2
    exit 1
  fi
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$SRC" ".backup '$DEST'"
  else
    cp "$SRC" "$DEST"
  fi
  gzip -f "$DEST"
  echo "==> SQLite backup written to ${DEST}.gz"
else
  DEST="$BACKUP_DIR/mandate-$STAMP.sql.gz"
  pg_dump "$DB_URL" | gzip > "$DEST"
  echo "==> Postgres dump written to $DEST"
fi

# Prune old backups, keeping the most recent $RETENTION files.
ls -1t "$BACKUP_DIR"/mandate-* 2>/dev/null | tail -n "+$((RETENTION + 1))" | xargs -r rm -f
echo "==> Retention applied (keep $RETENTION). Current backups:"
ls -1t "$BACKUP_DIR"/mandate-* 2>/dev/null | head -n "$RETENTION" || true
