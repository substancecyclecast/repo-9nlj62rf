#!/usr/bin/env bash
# SnabAgent — First-time server deployment script
# Run on a fresh Ubuntu 22.04+ server with root access
# Usage: curl -sSL <url> | bash
#   OR: bash scripts/deploy_first_time.sh

set -euo pipefail

echo "=== SnabAgent First-Time Deploy ==="
echo "Server: $(hostname)"
echo "Started: $(date -u)"
echo ""

# 1. System packages
echo "--- Installing system packages ---"
apt-get update -qq
apt-get install -y -qq docker.io docker-compose-plugin git curl ufw fail2ban

# 2. Enable and start Docker
systemctl enable docker
systemctl start docker

# 3. Firewall
echo "--- Configuring firewall ---"
ufw --force enable
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw reload

# 4. Create project directory
echo "--- Setting up project ---"
mkdir -p /opt/snabagent
cd /opt/snabagent

# If archive exists locally, use it; otherwise prompt
if [ -f snabagent_v2.0.0_production.zip ]; then
    unzip -o snabagent_v2.0.0_production.zip
elif [ -d snabagent ]; then
    echo "Project directory already exists."
else
    echo "ERROR: Place snabagent_v2.0.0_production.zip in /opt/snabagent/ and re-run."
    exit 1
fi

cd /opt/snabagent/snabagent

# 5. Create .env from template if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  ВАЖНО: отредактируйте .env перед запуском!"
    echo "   nano /opt/snabagent/snabagent/.env"
    echo ""
    echo "Минимально заполнить:"
    echo "  - SECRET_KEY (рандомная строка 64 символа)"
    echo "  - POSTGRES_PASSWORD"
    echo "  - DATABASE_URL"
    echo "  - LLM_GIGACHAT_AUTH_KEY"
    echo "  - TELEGRAM_BOT_TOKEN"
    echo "  - DOMAIN"
    echo ""
fi

# 6. Launch
echo "--- Starting services ---"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "--- Waiting for services to start ---"
sleep 15

# 7. Run migrations
docker compose exec -T api alembic upgrade head 2>/dev/null || echo "Migration skipped (may need DB first start)"

# 8. Health check
echo ""
echo "--- Health check ---"
curl -sf http://localhost:8000/health && echo " ✓ API is healthy" || echo " ✗ API not ready yet (may need more time)"

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env: nano /opt/snabagent/snabagent/.env"
echo "  2. Set DOMAIN to your real domain"
echo "  3. Point DNS A-record to this server's IP: $(curl -s ifconfig.me 2>/dev/null || echo 'N/A')"
echo "  4. Restart: docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"
echo "  5. Caddy will auto-obtain HTTPS certificate"
echo ""
echo "URLs:"
echo "  API:       https://\${DOMAIN}/docs"
echo "  Dashboard: https://\${DOMAIN}/"
echo "  Grafana:   https://\${DOMAIN}/grafana/"
echo "  Flower:    https://\${DOMAIN}/flower/"
