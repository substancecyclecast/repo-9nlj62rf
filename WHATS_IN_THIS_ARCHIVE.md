# Что в этом архиве

`snabagent_v2.2.0.zip` — enterprise-ready версия SnabAgent v2.2.0.

## Быстрая навигация

| Где | Что |
|---|---|
| `README.md` | Точка входа: установка, demo-режим, JWT, метрики, бенчмарк, compliance. |
| `CHANGELOG.md` | Полный changelog v2.2.0 (Keep a Changelog). |
| `PROJECT_OVERVIEW.md` | Описание продукта для инвестора/клиента с метриками. |
| `Makefile` | `make dev`, `make offline-demo`, `make check-all`, `make sbom`, `make openapi`, `make lock`. |
| `src/` | Production-код: API, агенты, БД, SSO, сервисы, бот, UI. |
| `tests/` | Юнит + интеграция + e2e тесты. |
| `scripts/` | Сидеры, offline-demo, benchmark, `backup.sh`, `restore.sh`. |
| `deploy/` | docker-compose (prod/dev), Caddyfile с TLS, Terraform. |
| `helm/` | Kubernetes Helm chart (Chart.yaml, values.yaml, templates). ← НОВЫЙ |
| `alembic/` | Миграции PostgreSQL. |
| `data/` | Ground-truth CSV, sample-TZ, benchmark_results.json. |
| `.streamlit/config.toml` | Конфигурация темы Streamlit (dark/light mode). ← НОВЫЙ |
| `.github/workflows/ci.yml` | CI: ruff, mypy (advisory), coverage gate ≥70%, bandit, pip-audit, offline-demo, benchmark. |

## Документация

| Файл | Описание |
|---|---|
| `docs/architecture.md` | Архитектура: 6 агентов, БД-схема, обвязка. |
| `docs/deployment.md` | Docker Compose, Kubernetes/Helm, миграции, rollback, TLS. ← НОВЫЙ |
| `docs/monitoring.md` | SLO, Prometheus, Grafana, alerting, runbook. ← НОВЫЙ |
| `docs/sso.md` | SSO: Azure AD, Keycloak, SAML 2.0, OAuth2/OIDC. ← НОВЫЙ |
| `docs/telegram_bot.md` | Telegram bot: команды, настройка, webhook. ← НОВЫЙ |
| `docs/bi_integration.md` | BI: CSV/JSON export, PowerBI, Tableau, DataLens. ← НОВЫЙ |
| `docs/security.md` | Безопасность: JWT, password policy, headers, audit. ← НОВЫЙ |
| `docs/demo_scenarios.md` | 3 готовых сценария (metals/IT/chemistry). |
| `docs/runbook.md` | Дежурный runbook (alert response, rollback). |

## Продажи и юридические документы

| Файл | Описание |
|---|---|
| `docs/sales/PITCH_DECK_PROMPT.md` | Промпт для AI-генерации pitch deck. ← НОВЫЙ |
| `docs/sales/pitch_deck_outline.md` | Outline для pitch deck. |
| `docs/legal/EULA.md` | Лицензионное соглашение. |
| `docs/legal/DPA.md` | Обработка персональных данных (152-ФЗ). |
| `docs/legal/SLA.md` | SLA с компенсациями. |
| `docs/legal/ToS.md` | Terms of Service (условия использования). ← НОВЫЙ |

## Новые модули (v2.2.0)

| Модуль | Путь | Описание |
|---|---|---|
| SSO SAML | `src/snabagent/api/sso/saml.py` | SAML 2.0 endpoints |
| SSO OAuth2 | `src/snabagent/api/sso/oauth2.py` | OAuth2/OIDC + PKCE |
| Export routes | `src/snabagent/api/routes/export.py` | CSV/JSON BI export |
| Circuit breaker | `src/snabagent/services/llm_client.py` | LLM retry + circuit breaker |
| Language detect | `src/snabagent/services/language.py` | RU/EN/KZ detection |
| Notifications | `src/snabagent/services/notifications.py` | Telegram/Slack/Webhook |
| Price predictor | `src/snabagent/services/price_predictor.py` | Historical price analysis |
| Metering | `src/snabagent/services/metering.py` | License usage tracking |
| Export service | `src/snabagent/services/export.py` | PDF/CSV/JSON generation |
| Email digest | `src/snabagent/services/email_digest.py` | Daily email template |
| Telegram bot | `src/snabagent/bot/telegram_bot.py` | Bot commands |

## Quality Gates (v2.2.0)

```text
ruff check src tests          → All checks passed!
mypy src/snabagent            → advisory (не блокирует CI; типизация дорабатывается)
pytest --cov-fail-under=70    → 238 passed, coverage 72%
bandit -r src -ll             → No issues
frontend: npm run lint        → 0 errors
frontend: npm run build       → OK
```

## Как запустить демо за 5 минут (offline, без LLM)

```bash
make install-dev       # Установит зависимости
make seed-users        # Создаст demo-пользователей
make offline-demo      # Прогонит 3 сценария end-to-end
make bench             # 10 ground-truth сценариев
```

## Продакшен (Docker)

```bash
cp .env.example .env
# Отредактировать .env: реальные ключи, DATABASE_URL, SECRET_KEY
make dev               # docker-compose up -d
make seed-users        # seed admin/buyer/viewer
# http://localhost:8501 — Streamlit (JWT-логин)
# http://localhost:8000/docs — API (Swagger UI)
# http://localhost:8000/health/ready — Health check
# http://localhost:8000/metrics — Prometheus
```

## Что НЕ в архиве (human tasks)

- Видео-демо (нужно записать спикером).
- Финальный дизайн pitch deck (промпт в `docs/sales/PITCH_DECK_PROMPT.md`).
- Подача в Роспатент (юридическая процедура клиента).
- Реальные LLM-ключи (предоставляет заказчик).
- Load test результаты (запускается на prod-инфраструктуре).

## Поддержка

См. `README.md` → раздел Support.
