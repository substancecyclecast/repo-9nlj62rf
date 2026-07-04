#!/usr/bin/env bash
# Convenience launcher for local development (backend + frontend).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend (FastAPI) on :8000"
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -q -r requirements.txt
( uvicorn app.main:app --reload --port 8000 & )

echo "==> Frontend (Next.js) on :3000"
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi
npm run dev
