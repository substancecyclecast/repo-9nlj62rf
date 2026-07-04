#!/usr/bin/env bash
# Деплой SnabAgent на готовую VM (после Terraform).
#
# Использование:
#   scp -r snabagent.zip ubuntu@<external_ip>:/opt/snabagent/
#   ssh ubuntu@<external_ip> 'cd /opt/snabagent && unzip snabagent.zip && ./deploy/yc/ansible/deploy_app.sh'
set -euo pipefail

APP_DIR="/opt/snabagent"
cd "$APP_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Скопирован .env.example в .env. ЗАПОЛНИТЕ ключи перед запуском."
  exit 1
fi

docker compose pull || true
docker compose build
docker compose up -d
docker compose exec -T api alembic upgrade head
docker compose exec -T api python scripts/generate_mock_suppliers.py || true
docker compose exec -T api python scripts/seed_db.py
docker compose exec -T api python scripts/seed_qdrant.py
echo "Готово. http://<external_ip>:8501"
