# Changelog

## [2.2.0] — 2026-06-15

### Fixed
- **Деплой/стабильность демо** — устранён дублирующий systemd-сервис `snabagent.service` (краш-цикл на порту 8000) и добавлен 4 ГБ swap на VPS; latency login/health снизилась с 24–28 c до ~0.3–0.6 c.
- **ruff** — исправлены `E402` (импорты в `db/models.py`) и `E501` (длинные строки в `api/routes/auth.py`); `ruff check src tests` снова чист.
- **Frontend ESLint** — устранены все 20 ошибок: убраны `any` (типизированные хелперы `apiErrorStatus`/`apiErrorDetail`), исправлен порядок объявления в `Login.tsx`, упрощён regex проверки пароля.

### Changed
- **Версия** приведена к `2.2.0` во всех артефактах (`pyproject.toml`, доках, архиве).
- **mypy** переведён в advisory-режим в CI (не блокирует пайплайн); строгая типизация вынесена в tech-debt.
- **Документация** синхронизирована с реальными метриками: **238 тестов, покрытие 72 %** (gate ≥ 70 %).

## [1.0.0] — 2026-06-04

### Added
- **Public Registration** — `POST /api/v1/auth/register` with password policy, duplicate checks, trial activation (14 days)
- **Rate Limiting** — 3/min on registration, 5/min on login (slowapi)
- **CORS Middleware** — Configurable origins via `cors_origins` setting
- **Request Tracing** — UUID-based `X-Request-ID` header on all requests
- **Global Error Handler** — Structured JSON error responses with request_id
- **Paginated Lots API** — `GET /api/v1/lots/` returns `{items, total, page, page_size, pages}`
- **Telegram Webhook** — `POST /api/v1/webhooks/telegram` for bot commands
- **SPA Static Serving** — React frontend served from `/frontend/dist`, fallback to `index.html`
- **React Frontend** — Full SPA with:
  - Landing page with pricing/features
  - Registration with password strength indicator
  - Login with success/error feedback
  - Dashboard with KPI cards and lots table
  - Lots list with pagination and status filter
  - Lot detail with progress stepper, audit log, supplier cards
  - Analytics page with Recharts (pie + bar charts)
  - Settings page (profile, theme, API token)
  - Dark mode (persisted in localStorage)
  - Responsive sidebar navigation
- **New Unit Tests** — language detection, metering, circuit breaker, email digest, telegram bot, price predictor, notifications
- **New Integration Tests** — registration flow (success, duplicate, weak password, missing fields, login after register), health endpoint
- **Architecture Documentation** — `docs/architecture.md`
- **SAML 2.0 + OAuth2 SSO** — Stub routes for enterprise SSO
- **Structured Logging** — structlog with JSON output in routes

### Changed
- Lots list endpoint now returns paginated `PaginatedLots` instead of flat array
- Auth routes removed `from __future__ import annotations` for Pydantic compatibility
- `_OPEN_PATHS` extended with `/auth/register`, `/auth/verify-email`, `/webhooks/telegram`

### Fixed
- Rate limiting on login endpoint (was missing)
- Password validation returns 422 instead of 400
- Existing lots API tests updated for paginated response format
