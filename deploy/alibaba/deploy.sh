#!/usr/bin/env bash
# SnabAgent — one-shot deployment on a fresh Alibaba Cloud ECS instance (Ubuntu 22.04).
# Run ON the ECS box (as a sudo-capable user), from the repo root:
#   bash deploy/alibaba/deploy.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> [1/4] Installing Docker + Compose plugin (if missing)"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi

echo "==> [2/4] Preparing .env"
if [ ! -f .env ]; then
  cp deploy/alibaba/.env.alibaba.example .env
  echo "    Created .env from template. EDIT it now and set LLM_QWEN_API_KEY, then re-run."
  exit 1
fi
if grep -q "sk-your-dashscope-key" .env; then
  echo "    ERROR: LLM_QWEN_API_KEY is still the placeholder. Set your real Qwen key in .env." >&2
  exit 1
fi

echo "==> [3/4] Building and starting the stack (Qwen-powered)"
docker compose -f deploy/alibaba/docker-compose.alibaba.yml up -d --build

echo "==> [4/4] Seeding demo data (NSI + suppliers + Qdrant index)"
docker compose -f deploy/alibaba/docker-compose.alibaba.yml exec -T api \
  python scripts/seed_db.py || echo "    (seed_db skipped/failed — run manually if needed)"
docker compose -f deploy/alibaba/docker-compose.alibaba.yml exec -T api \
  python scripts/seed_qdrant.py || echo "    (seed_qdrant skipped/failed — run manually if needed)"

PUBLIC_IP="$(curl -s http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || curl -s ifconfig.me 2>/dev/null || echo YOUR_ECS_IP)"
cat <<EOF

==================================================================
 SnabAgent is up on Alibaba Cloud ECS (LLM = Qwen Cloud)
   API (FastAPI docs): http://${PUBLIC_IP}:8000/docs
   Streamlit UI:       http://${PUBLIC_IP}:8501
 Open ECS Security Group ports 8000 and 8501 to reach them.
==================================================================
EOF
