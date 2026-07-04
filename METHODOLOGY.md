# SnabAgent — Полная методичка

> Руководство по установке, настройке, деплою и использованию платформы
> Версия 2.2.0 | Июнь 2026

---

## Содержание

1. [Обзор проекта](#1-обзор-проекта)
2. [Архитектура](#2-архитектура)
3. [Требования к окружению](#3-требования-к-окружению)
4. [Локальная установка (Dev)](#4-локальная-установка-dev)
5. [Структура проекта](#5-структура-проекта)
6. [Backend (FastAPI)](#6-backend-fastapi)
7. [Frontend (React)](#7-frontend-react)
8. [Telegram-бот](#8-telegram-бот)
9. [Деплой на сервер (Production)](#9-деплой-на-сервер-production)
10. [Деплой фронтенда (Vercel)](#10-деплой-фронтенда-vercel)
11. [Конфигурация и переменные окружения](#11-конфигурация-и-переменные-окружения)
12. [API документация](#12-api-документация)
13. [Демо-режим](#13-демо-режим)
14. [Безопасность](#14-безопасность)
15. [Мониторинг и логирование](#15-мониторинг-и-логирование)
16. [Обновление и обслуживание](#16-обновление-и-обслуживание)
17. [Решение проблем (FAQ)](#17-решение-проблем-faq)
18. [Что нужно сделать вручную](#18-что-нужно-сделать-вручную)

---

## 1. Обзор проекта

**SnabAgent** — мульти-агентная AI-платформа для автоматизации корпоративных закупок.

Ключевые компоненты:
- **6 AI-агентов** (LangGraph): Planner → Sourcer → Communicator → Negotiator → Verifier → Reporter
- **Backend API** (FastAPI + PostgreSQL + Redis)
- **Frontend SPA** (React 19 + Vite + Tailwind CSS)
- **Telegram-бот** (@SnabAgent_Bot)
- **Двойная верификация** для защиты от галлюцинаций AI

---

## 2. Архитектура

```
Пользователь (браузер)
        │ HTTPS
        ▼
    Vercel (frontend)
        │ Vercel rewrites (proxy)
        ▼
    VPS 185.192.23.161
        │ HTTP :8000
        ▼
    FastAPI (uvicorn)
        │
   ┌────┼────────┬──────────┐
   │    │        │          │
   ▼    ▼        ▼          ▼
 PgSQL Redis  Qdrant    Celery Workers
                              │
                              ▼
                         LangGraph Pipeline
                         (6 AI-агентов)
```

**Решение Mixed Content:**
Фронтенд на Vercel (HTTPS) → Vercel rewrites проксируют `/api/*` запросы → бэкенд на VPS (HTTP). Браузер видит только HTTPS, нет Mixed Content.

---

## 3. Требования к окружению

### Для разработки (Dev)
- Python 3.11+
- Node.js 20+ (LTS)
- PostgreSQL 16+
- Redis 7+
- Docker + Docker Compose (рекомендуется)

### Для продакшена (VPS)
- Ubuntu 22.04 LTS
- 2 CPU / 2 GB RAM (минимум)
- Python 3.11 (через venv)
- PostgreSQL 16 (Docker или standalone)
- Redis 7 (Docker)
- nginx (reverse proxy)
- systemd (управление сервисами)

---

## 4. Локальная установка (Dev)

### 4.1. Клонирование и подготовка

```bash
# Распаковать архив или клонировать
cd snabagent

# Создать виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.lock

# Или через pyproject.toml:
pip install -e ".[dev]"
```

### 4.2. Настройка .env

```bash
cp .env.example .env
# Отредактировать .env (см. раздел 11)
```

### 4.3. Запуск через Docker Compose (рекомендуется)

```bash
docker compose up -d     # PostgreSQL + Redis + Qdrant
```

### 4.4. Миграции базы данных

```bash
export PYTHONPATH=src
alembic upgrade head
```

### 4.5. Запуск backend

```bash
export PYTHONPATH=src
uvicorn snabagent.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.6. Запуск frontend

```bash
cd frontend
npm install
npm run dev
# Откроется http://localhost:5173
```

### 4.7. Проверка

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"snabagent","env":"dev"}
```

---

## 5. Структура проекта

```
snabagent/
├── src/snabagent/           # Backend Python-код
│   ├── agents/              # 6 LangGraph-агентов
│   │   ├── pipeline.py      # Основной граф агентов
│   │   ├── prompts/         # Системные промпты для каждого агента
│   │   └── tools/           # Инструменты агентов (web search, etc.)
│   ├── api/                 # FastAPI application
│   │   ├── main.py          # Entry point (CORS, middleware, routers)
│   │   ├── routes/          # REST endpoints
│   │   │   ├── auth.py      # Регистрация, логин, JWT
│   │   │   ├── lots.py      # CRUD лотов
│   │   │   └── telegram_webhook.py
│   │   ├── sso/             # SSO/SAML/OAuth2
│   │   └── schemas/         # Pydantic-схемы
│   ├── bot/                 # Telegram bot
│   │   ├── telegram_bot.py  # Обработчики команд
│   │   └── polling_runner.py # Polling-режим запуска
│   ├── db/                  # База данных
│   │   ├── models.py        # SQLAlchemy модели
│   │   ├── repos.py         # Репозитории (CRUD)
│   │   └── session.py       # AsyncSession factory
│   ├── llm/                 # LLM-провайдеры
│   │   ├── router.py        # Мультимодельный роутер
│   │   ├── gigachat.py      # GigaChat интеграция
│   │   ├── yandexgpt.py     # YandexGPT интеграция
│   │   └── fake.py          # Заглушка для демо
│   ├── services/            # Бизнес-логика
│   ├── settings.py          # Конфигурация (pydantic-settings)
│   └── tasks/               # Celery-задачи
├── frontend/                # React SPA
│   ├── src/
│   │   ├── pages/           # Страницы (Landing, Dashboard, etc.)
│   │   ├── components/      # Переиспользуемые компоненты
│   │   ├── context/         # React Context (Auth, Theme)
│   │   └── api/client.ts    # Axios HTTP-клиент
│   ├── public/
│   │   └── logo.png         # Логотип SnabAgent
│   └── vercel.json          # Vercel rewrites (API proxy)
├── alembic/                 # Миграции БД
├── tests/                   # Тесты (238 штук)
├── deploy/                  # Конфиги деплоя
├── docker-compose.yml       # Dev-окружение
└── .env                     # Переменные окружения
```

---

## 6. Backend (FastAPI)

### 6.1. Основные маршруты

| Путь | Метод | Описание |
|------|-------|----------|
| `/health` | GET | Проверка состояния |
| `/api/v1/auth/register` | POST | Регистрация |
| `/api/v1/auth/login` | POST | Авторизация (JWT) |
| `/api/v1/auth/refresh` | POST | Обновление токена |
| `/api/v1/lots` | GET/POST | Список/создание лотов |
| `/api/v1/lots/{id}` | GET | Детали лота |
| `/api/v1/lots/{id}/approve` | POST | Одобрение лота |
| `/api/v1/lots/import-excel` | POST | Импорт из Excel |

### 6.2. Аутентификация

JWT-токены:
- **access_token**: 15 минут, передаётся в `Authorization: Bearer <token>`
- **refresh_token**: 7 дней, для обновления access_token
- API-ключ: передаётся в `X-Api-Key: <key>` (для интеграций)

### 6.3. Модели данных (SQLAlchemy)

Основные таблицы:
- `users` — пользователи (email, hashed_password, role, customer_id)
- `lots` — заявки на закупку (status, raw_request, ai_result, etc.)
- `customers` — организации (multi-tenancy)
- `audit_log` — лог всех действий

### 6.4. AI-агенты (LangGraph)

Пайплайн обработки лота:
```
draft → planned → sourcing → rfq_sent → responses_collected
  → negotiating → verified → report_ready → [approved | rejected | escalated]
```

Каждый агент — узел в графе LangGraph. Переходы управляются условными рёбрами.

---

## 7. Frontend (React)

### 7.1. Технологии
- React 19 + TypeScript
- Vite (сборка)
- Tailwind CSS 4 (стили)
- React Router 7 (маршрутизация)
- Axios (HTTP-клиент)
- Recharts (графики в Analytics)
- Lucide React (иконки)

### 7.2. Страницы
| Маршрут | Компонент | Описание |
|---------|-----------|----------|
| `/` | Landing | Главная страница с описанием продукта |
| `/login` | Login | Авторизация + демо-доступ |
| `/register` | Register | Регистрация |
| `/dashboard` | Dashboard | KPI + таблица лотов |
| `/lots` | Lots | Полный список лотов |
| `/lots/:id` | LotDetail | Детали конкретного лота |
| `/analytics` | Analytics | Графики и аналитика |
| `/settings` | Settings | Настройки профиля + API-ключи |

### 7.3. API-клиент

Файл: `frontend/src/api/client.ts`

```typescript
const api = axios.create({
  baseURL: '/api/v1',  // Относительный путь — проксируется Vercel
});
```

Интерцепторы автоматически:
- Добавляют JWT-токен из localStorage
- Обновляют токен при 401

---

## 8. Telegram-бот

### 8.1. Текущий режим: Long Polling

Бот работает в polling-режиме (не требует HTTPS). Управляется systemd.

### 8.2. Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/new <текст заявки>` | Создать новую заявку |
| `/status` | Показать текущие лоты |
| `/lot <id>` | Детали лота |
| `/approve <id>` | Одобрить лот |
| `/escalate <id>` | Эскалация |
| `/help` | Справка |

### 8.3. Файлы

- `src/snabagent/bot/telegram_bot.py` — обработчики команд
- `src/snabagent/bot/polling_runner.py` — polling-запуск
- Сервис: `/etc/systemd/system/snabagent-bot.service`

---

## 9. Деплой на сервер (Production)

### 9.1. Подготовка VPS

```bash
# Подключение
ssh root@185.192.23.161

# Обновление системы
apt update && apt upgrade -y

# Установка Python 3.11
apt install -y python3.11 python3.11-venv python3.11-dev

# Установка nginx
apt install -y nginx
```

### 9.2. Копирование файлов

```bash
# С локальной машины:
rsync -avz --exclude='venv' --exclude='node_modules' \
  --exclude='__pycache__' --exclude='.git' \
  ./snabagent/ root@185.192.23.161:/opt/snabagent/
```

### 9.3. Настройка виртуального окружения

```bash
cd /opt/snabagent
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.lock
```

### 9.4. Настройка .env

```bash
nano /opt/snabagent/.env
# См. раздел 11 для всех переменных
```

### 9.5. Запуск PostgreSQL + Redis (Docker)

```bash
# PostgreSQL
docker run -d --name snabagent-db \
  -e POSTGRES_USER=liquidity \
  -e POSTGRES_PASSWORD=liquidity_secret \
  -e POSTGRES_DB=snabagent \
  -p 5432:5432 \
  postgres:16-alpine

# Redis
docker run -d --name snabagent-redis \
  -p 6380:6379 \
  redis:7-alpine
```

### 9.6. Миграции

```bash
cd /opt/snabagent
source venv/bin/activate
export PYTHONPATH=/opt/snabagent/src
alembic upgrade head
```

### 9.7. Systemd-сервисы

**API-сервер:** `/etc/systemd/system/snabagent-api.service`
```ini
[Unit]
Description=SnabAgent API Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/snabagent
Environment=PYTHONPATH=/opt/snabagent/src
EnvironmentFile=/opt/snabagent/.env
ExecStart=/opt/snabagent/venv/bin/uvicorn snabagent.api.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level warning
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Telegram-бот:** `/etc/systemd/system/snabagent-bot.service`
```ini
[Unit]
Description=SnabAgent Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/snabagent
Environment=PYTHONPATH=/opt/snabagent/src
EnvironmentFile=/opt/snabagent/.env
ExecStart=/opt/snabagent/venv/bin/python -m snabagent.bot.polling_runner
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable snabagent-api snabagent-bot
systemctl start snabagent-api snabagent-bot
```

### 9.8. nginx конфигурация

```nginx
server {
    listen 80;
    server_name 185.192.23.161;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    client_max_body_size 10M;
}
```

---

## 10. Деплой фронтенда (Vercel)

### 10.1. Сборка

```bash
cd frontend
npm install
npm run build   # Собирает в dist/
```

### 10.2. Деплой на Vercel

```bash
# Установка Vercel CLI
npm install -g vercel

# Деплой (production)
vercel --token <VERCEL_TOKEN> --prod --yes
```

### 10.3. vercel.json (API proxy)

Файл `frontend/vercel.json`:
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "http://185.192.23.161:8000/api/:path*"
    },
    {
      "source": "/health",
      "destination": "http://185.192.23.161:8000/health"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

Это решает проблему Mixed Content: все API-запросы идут через HTTPS-домен Vercel, который проксирует их на HTTP-бэкенд.

---

## 11. Конфигурация и переменные окружения

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `APP_ENV` | Окружение | `dev` / `production` |
| `SECRET_KEY` | Ключ для JWT | `<random 64 chars>` |
| `API_KEY` | API-ключ для интеграций | `dev-7fIc3ibt...` |
| `DEMO_MODE` | Включить демо-режим | `true` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis URL | `redis://localhost:6380/0` |
| `QDRANT_HOST` | Qdrant хост | `localhost` |
| `QDRANT_PORT` | Qdrant порт | `6333` |
| `EMBEDDING_BACKEND` | Бэкенд эмбеддингов | `fake` / `openai` / `sentence-transformers` |
| `LLM_PRIMARY` | Основной LLM | `fake` / `gigachat` / `yandexgpt` |
| `LLM_VERIFIER` | LLM для верификации | `fake` / `gigachat` |
| `CORS_ORIGINS` | Разрешённые origins | `["https://snab-agent.vercel.app","*"]` |
| `FRONTEND_URL` | URL фронтенда | `https://snab-agent.vercel.app` |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота | `<TELEGRAM_BOT_TOKEN>` |
| `PYTHONPATH` | Путь к исходникам | `/opt/snabagent/src` |

---

## 12. API документация

После запуска бэкенда доступны:
- **Swagger UI:** http://185.192.23.161:8000/docs
- **ReDoc:** http://185.192.23.161:8000/redoc
- **OpenAPI JSON:** http://185.192.23.161:8000/openapi.json

---

## 13. Демо-режим

Когда `DEMO_MODE=true`:
- При первом входе демо-пользователя автоматически создаётся аккаунт с 5 примерами лотов
- Лоты демонстрируют разные стадии пайплайна
- Email: `demo@snabagent.ru`, пароль: `Demo123!@#`
- URL: https://snab-agent.vercel.app/login?demo=true

---

## 14. Безопасность

### 14.1. Аутентификация
- JWT (access 15 мин, refresh 7 дней)
- bcrypt для хэширования паролей
- Политика паролей: 8+ символов, цифра, спецсимвол

### 14.2. Авторизация
- RBAC: admin, buyer, viewer
- customer_id isolation (multi-tenancy)
- Row-Level Security в БД

### 14.3. Сетевая безопасность
- Mixed Content решён через Vercel proxy
- CORS ограничен списком разрешённых origins
- Rate limiting по IP и endpoint
- PII маскируется перед отправкой в LLM

### 14.4. Рекомендации по усилению
- [ ] Установить SSL на VPS (certbot + nginx)
- [ ] Включить fail2ban для защиты SSH
- [ ] Настроить firewall (ufw)
- [ ] Регулярный аудит зависимостей (`pip-audit`, `npm audit`)

---

## 15. Мониторинг и логирование

### 15.1. Health check
```bash
curl http://185.192.23.161:8000/health
```

### 15.2. Логи сервисов
```bash
# API логи
journalctl -u snabagent-api -f

# Bot логи
journalctl -u snabagent-bot -f

# nginx логи
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 15.3. Статус сервисов
```bash
systemctl status snabagent-api
systemctl status snabagent-bot
docker ps  # PostgreSQL + Redis
```

---

## 16. Обновление и обслуживание

### 16.1. Обновление backend

```bash
# На локальной машине:
rsync -avz --exclude='venv' --exclude='__pycache__' \
  src/ root@185.192.23.161:/opt/snabagent/src/

# На сервере:
ssh root@185.192.23.161
cd /opt/snabagent && source venv/bin/activate
export PYTHONPATH=/opt/snabagent/src
alembic upgrade head      # Если есть новые миграции
systemctl restart snabagent-api
systemctl restart snabagent-bot
```

### 16.2. Обновление frontend

```bash
cd frontend
npm install
npm run build
vercel --token <TOKEN> --prod --yes
```

### 16.3. Бэкапы

```bash
# Бэкап PostgreSQL
docker exec snabagent-db pg_dump -U liquidity snabagent > backup_$(date +%Y%m%d).sql

# Восстановление
cat backup_YYYYMMDD.sql | docker exec -i snabagent-db psql -U liquidity snabagent
```

---

## 17. Решение проблем (FAQ)

### Mixed Content в браузере
**Проблема:** Браузер блокирует HTTP-запросы со страницы HTTPS.
**Решение:** Настроен `vercel.json` с rewrites — все `/api/*` запросы проксируются через Vercel (HTTPS → HTTP).

### Текст накладывается в панели управления
**Проблема:** CSS flex-контейнеры не ограничивают ширину текста.
**Решение:** Добавлены `min-w-0`, `truncate`, `shrink-0` в KPI-карточки и sidebar.

### Backend не запускается (порт занят)
```bash
fuser -k 8000/tcp
systemctl restart snabagent-api
```

### Telegram-бот не отвечает
```bash
systemctl status snabagent-bot
journalctl -u snabagent-bot -n 50
# Проверить TELEGRAM_BOT_TOKEN в .env
systemctl restart snabagent-bot
```

### Ошибки миграций БД
```bash
cd /opt/snabagent
source venv/bin/activate
export PYTHONPATH=/opt/snabagent/src
alembic current          # Текущая ревизия
alembic upgrade head     # Применить все миграции
```

### Vercel деплой не обновляется
```bash
cd frontend
npm run build
vercel --token <TOKEN> --prod --yes --force
```

---

## 18. Что нужно сделать вручную

Следующие задачи требуют ручного выполнения человеком:

1. **Установка SSL/HTTPS на VPS** — требуется домен (Let's Encrypt не работает по IP). Нужно:
   - Зарегистрировать домен (например, api.snabagent.ru)
   - Настроить DNS A-запись → 185.192.23.161
   - Запустить `certbot --nginx -d api.snabagent.ru`

2. **Подключение реальных LLM** — сейчас используются FakeLLM (заглушки). Нужно:
   - Получить API-ключи GigaChat / YandexGPT
   - Обновить `.env`: `LLM_PRIMARY=gigachat`, `GIGACHAT_API_KEY=...`

3. **Настройка SMTP для реальных RFQ** — сейчас email не отправляются. Нужно:
   - Настроить SMTP-сервер (Yandex Business / Mail.ru для бизнеса)
   - Обновить `.env`: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`

4. **Регистрация бизнеса** — ООО, товарный знак, оферта (юридические вопросы)

5. **Заполнение слайда "Команда"** в презентации — информация об основателе

6. **Настройка CI/CD** — GitHub Actions для автоматического деплоя

7. **Подключение Sentry** — для мониторинга ошибок в production

---

*SnabAgent v2.2.0 | Июнь 2026*
