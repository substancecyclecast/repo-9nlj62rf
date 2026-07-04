# SnabAgent — Архитектура

## Обзор

SnabAgent — мульти-агентная система автоматизации закупок с AI-движком.  
Платформа автоматически парсит заявки, ищет поставщиков, ведёт переговоры и формирует отчёты.

## Стек технологий

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x (async), PostgreSQL |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS 4 |
| AI/ML | LangChain, LangGraph, OpenAI/YandexGPT/Anthropic, sentence-transformers |
| Vector DB | Qdrant |
| Queue | Celery + Redis |
| Monitoring | Prometheus, structlog |
| Auth | JWT (access + refresh), bcrypt, SAML 2.0, OAuth2 |

## Компоненты

```
┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│   Frontend   │───▶│   FastAPI     │───▶│  PostgreSQL    │
│  React+Vite  │    │   Backend    │    │  (SQLAlchemy)  │
└─────────────┘    └──────┬───────┘    └────────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌─────────┐ ┌─────────┐
        │ LangGraph │ │ Qdrant  │ │  Redis  │
        │  Agents   │ │ VectorDB│ │ Celery  │
        └──────────┘ └─────────┘ └─────────┘
```

## Агенты (LangGraph)

1. **Planner** — парсит сырую заявку, определяет категорию, извлекает позиции
2. **Sourcer** — ищет поставщиков через NSI-индекс и веб-скрейпинг
3. **Communicator** — формирует и отправляет RFQ-запросы
4. **Negotiator** — анализирует ответы, ведёт переговоры по цене
5. **Verifier** — перекрёстная проверка результатов другой LLM
6. **Reporter** — формирует финальный отчёт с top-3 и экономией

## Пайплайн лота

```
draft → planned → sourcing → rfq_sent → responses_collected
  → negotiating → verified → report_ready → approved/rejected
```

Эскалация (`escalated`) происходит при:
- Низкой уверенности верификатора
- Несоответствии регуляторным ограничениям
- Превышении бюджета > 15%

## API

### Публичные эндпоинты (без API key)
- `POST /api/v1/auth/register` — регистрация (3/мин)
- `POST /api/v1/auth/login` — логин (5/мин)
- `GET /api/v1/auth/verify-email` — верификация email
- `POST /api/v1/webhooks/telegram` — Telegram webhook
- `GET /health` — healthcheck

### Защищённые эндпоинты (JWT / API key)
- `GET/POST /api/v1/lots` — CRUD лотов
- `GET /api/v1/lots/{id}/audit` — audit log
- `POST /api/v1/lots/{id}/approve` — одобрение
- `GET /api/v1/auth/me` — текущий пользователь
- `WS /ws/lots/{id}` — realtime обновления

## Безопасность

- JWT access tokens (15 мин) + refresh tokens
- Bcrypt хеширование паролей (password policy: 8+ символов, цифра, спецсимвол)
- Rate limiting (slowapi)
- CORS с настраиваемыми origins
- Request ID tracing (UUID)
- PII маскирование в логах
- Bandit security scanning

## Frontend

React SPA с поддержкой:
- Тёмной темы (localStorage)
- Responsive layout (мобильная навигация)
- Авторизации через JWT
- Графиков (Recharts)
- Пагинации
