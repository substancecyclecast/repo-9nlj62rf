# Mandate — Полный гайд по деплою

## Оглавление
1. [Архитектура деплоя](#1-архитектура-деплоя)
2. [Вариант 1: Vercel (Frontend) + Railway/Render (Backend)](#2-vercel--railwayrender)
3. [Вариант 2: Vercel (Fullstack с Serverless)](#3-vercel-fullstack)
4. [Вариант 3: Docker на VPS (DigitalOcean/Hetzner)](#4-docker-на-vps)
5. [База данных](#5-база-данных)
6. [Environment Variables](#6-environment-variables)
7. [Домен и DNS](#7-домен-и-dns)
8. [CI/CD](#8-cicd)

---

## 1. Архитектура деплоя

```
[Пользователь] → [Vercel CDN / Frontend] → [Backend API] → [PostgreSQL]
                                                ↓
                              [Stellar Horizon] [Soroban RPC] [Anchors]
```

**Компоненты:**
- **Frontend** (Next.js 14) — статический + SSR, идеально для Vercel
- **Backend** (FastAPI/Python) — API сервер, нужен Python runtime
- **Database** — SQLite (dev) / PostgreSQL (prod)

---

## 2. Vercel (Frontend) + Railway/Render (Backend)

### Рекомендуемый вариант для продакшена

Это лучший вариант: Vercel для фронта (бесплатно, быстро, CDN), Railway/Render для Python бэкенда.

### Шаг 1: Деплой Backend на Railway

1. Зайди на https://railway.app и подключи GitHub
2. Создай новый проект → "Deploy from GitHub repo"
3. Выбери репо `wltxipiv`, укажи root directory: `backend`
4. Railway автоматически определит Python — добавь:

**railway.toml** (создать в `backend/`):
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/docs"
restartPolicyType = "on_failure"
```

5. Добавь переменные окружения в Railway Dashboard:
```
DATABASE_URL=postgresql://user:pass@host:5432/mandate
MANDATE_LLM_PROVIDER=anthropic  (опционально)
ANTHROPIC_API_KEY=sk-...        (опционально)
```

6. Railway даст URL типа: `https://mandate-backend-production.up.railway.app`

**Альтернатива — Render.com:**
1. https://render.com → New Web Service
2. Root Directory: `backend`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Instance Type: Free (для демо) или Starter $7/мес

### Шаг 2: Деплой Frontend на Vercel

1. Зайди на https://vercel.com и подключи GitHub
2. Import проект `wltxipiv`
3. **Framework Preset:** Next.js
4. **Root Directory:** `frontend`
5. **Environment Variables:**
```
NEXT_PUBLIC_API_URL=https://mandate-backend-production.up.railway.app
```

6. Нажми "Deploy" — Vercel автоматически соберёт Next.js

### Шаг 3: Настрой CORS на бэкенде

В `backend/app/main.py` уже есть CORS middleware. Убедись, что Vercel домен добавлен:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mandate.vercel.app", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Шаг 4: Настрой проксирование в Next.js

В `frontend/next.config.mjs`:
```javascript
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`,
      },
    ];
  },
};
export default nextConfig;
```

---

## 3. Vercel Fullstack (с Serverless Functions)

### Если хочешь всё на Vercel

⚠️ **Ограничение:** Vercel Serverless Functions имеют лимит 10s (free) / 60s (pro). Для большинства API endpoints этого достаточно, но для тяжёлых операций (batch payroll) может не хватить.

### Вариант A: Vercel + External API

Лучший подход — деплоить только фронт на Vercel, а бэкенд на Railway (см. выше).

### Вариант B: Конвертация в Vercel Functions (не рекомендуется)

Потребует переписать бэкенд на Vercel Serverless (Python runtime). Не рекомендую — проще Railway.

---

## 4. Docker на VPS (DigitalOcean/Hetzner)

### Для полного контроля

### Шаг 1: Арендуй VPS
- **DigitalOcean:** $6/мес (1 vCPU, 1GB RAM) — достаточно для демо
- **Hetzner:** €3.79/мес (2 vCPU, 2GB RAM) — лучшее соотношение цена/качество
- **AWS Lightsail:** $3.50/мес

### Шаг 2: Установи Docker

```bash
ssh root@your-server-ip
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin
```

### Шаг 3: Клонируй и запусти

```bash
git clone https://github.com/Nadirpliline/wltxipiv.git
cd wltxipiv
docker compose up -d --build
```

### Шаг 4: Настрой Nginx + SSL

```bash
apt install nginx certbot python3-certbot-nginx

# Nginx config
cat > /etc/nginx/sites-available/mandate << 'EOF'
server {
    server_name mandate.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/mandate /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL
certbot --nginx -d mandate.yourdomain.com
```

---

## 5. База данных

### Для демо/акселератора
SQLite работает из коробки, ничего настраивать не нужно.

### Для продакшена
Рекомендую **Neon** (бесплатный PostgreSQL):
1. https://neon.tech → Create Project
2. Скопируй connection string
3. Установи переменную: `DATABASE_URL=postgresql://...`

**Альтернативы:**
- **Supabase** — бесплатный PostgreSQL + auth
- **Railway** — встроенный PostgreSQL ($5/мес)
- **PlanetScale** — MySQL (бесплатный tier)

---

## 6. Environment Variables

### Обязательные для продакшена:
```env
# Database (если не SQLite)
DATABASE_URL=postgresql://user:pass@host:5432/mandate

# Frontend
NEXT_PUBLIC_API_URL=https://api.mandate.yourdomain.com
```

### Опциональные (для LLM agent mode):
```env
MANDATE_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
# или
MANDATE_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Для будущей live интеграции (не нужны для демо):
```env
# Stellar
STELLAR_NETWORK=testnet  # или public для mainnet
STELLAR_HORIZON_URL=https://horizon-testnet.stellar.org

# Off-ramp
BRIDGE_API_KEY=...

# Compliance
CHAINALYSIS_API_KEY=...
```

### Production ops (мониторинг, уведомления, биллинг, rate limiting):
```env
# Rate limiting (по умолчанию выключен; включай на публичном API)
MANDATE_RATE_LIMIT_ENABLED=true
MANDATE_RATE_LIMIT_PER_MINUTE=120

# Event-уведомления (Slack / Telegram). Если не заданы — доставка со статусом "skipped"
MANDATE_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
MANDATE_TELEGRAM_BOT_TOKEN=...
MANDATE_TELEGRAM_CHAT_ID=...

# Биллинг (take-rate в bps + платформенный fee/мес)
MANDATE_BILLING_TAKE_RATE_BPS=25
MANDATE_BILLING_PLATFORM_FEE_USD=2000
```

**Эндпоинты для оркестрации/мониторинга** (не требуют ключей):
- `GET /healthz` — liveness probe
- `GET /readyz` — readiness probe (проверяет БД), для Kubernetes/Railway healthcheck
- `GET /metrics` — Prometheus-формат (настрой scrape в Prometheus/Grafana Agent)

**Бэкапы БД:** запускай `scripts/backup_db.sh` по cron (поддерживает SQLite online-backup
и `pg_dump` для Postgres, с ретеншеном). Пример: `0 * * * * /app/scripts/backup_db.sh`.

**API-документация:** Swagger доступен на `/docs`, ReDoc на `/redoc`. Сгенерировать
статический `openapi.json` + Postman-коллекцию: `python scripts/export_openapi.py`
(пишет в `docs/api/`).

---

## 7. Домен и DNS

### Рекомендуемая структура:
- `mandate.finance` или `getmandate.io` — лендинг
- `app.mandate.finance` — приложение (Vercel)
- `api.mandate.finance` — бэкенд (Railway)

### Настройка DNS (Cloudflare/Namecheap):
```
A     app     76.76.21.21        (Vercel)
CNAME api     mandate-backend.up.railway.app
CNAME www     mandate.finance
```

### На Vercel:
Settings → Domains → Add `app.mandate.finance`

---

## 8. CI/CD

### GitHub Actions (рекомендуется)

Создай `.github/workflows/deploy.yml`:

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install & test backend
        run: |
          cd backend
          pip install -r requirements.txt
          PYTHONPATH=. pytest -q
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Build frontend
        run: |
          cd frontend
          npm install
          npm run build

  deploy-backend:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: mandate-backend

  deploy-frontend:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      # Vercel auto-deploys on push — no action needed
      - run: echo "Vercel deploys automatically on push to main"
```

---

## Быстрый старт (5 минут до живого демо)

**Самый быстрый путь для демо акселератору:**

1. Push код в main branch на GitHub
2. Зайди на https://railway.app → Deploy from repo (root: `backend`)
3. Зайди на https://vercel.com → Import repo (root: `frontend`)
4. Добавь `NEXT_PUBLIC_API_URL` в Vercel env vars
5. Готово — живое демо на `your-project.vercel.app`

**Общее время:** ~5 минут (без домена) или ~15 минут (с кастомным доменом).

---

## Чеклист перед подачей

- [ ] Backend задеплоен и отвечает на /docs
- [ ] Frontend задеплоен и показывает дашборд
- [ ] API проксирование работает (фронт видит бэкенд)
- [ ] Демо данные загружаются (Stellar карты видны)
- [ ] Cross-border калькулятор работает
- [ ] Payroll batch выполняется
- [ ] Кастомный домен настроен (опционально)
- [ ] SSL сертификат установлен (авто на Vercel/Railway)
