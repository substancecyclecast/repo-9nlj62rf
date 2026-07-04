# SnabAgent — AI-платформа автоматизации корпоративных закупок

> Версия 2.2.0 | Обновлено: Июнь 2026

## Общее описание

**SnabAgent** — автономная мульти-агентная AI-платформа для автоматизации корпоративных закупок.

**Ценностное предложение:**
«Грязная» заявка на закупку → 6 поставщиков → 3 коммерческих предложения → сравнительная таблица с обоснованием НМЦК — всё за 15 минут вместо 3-5 дней.

**Целевые клиенты:** крупные промышленные компании (SIBUR, Полиметалл, Газпром нефть), управляющие тысячами SKU ежемесячно.

---

## Проблема

Корпоративные закупки в России:
- **Медленно:** 3-5 рабочих дней на один лот, 6-8 ручных операций
- **Непрозрачно:** нет видимости в историю цен поставщиков
- **Рискованно:** ошибки в соответствии ГОСТ/ТУ, 44-ФЗ/223-ФЗ
- **Дорого:** потери 15-40% от неоптимальных цен
- **Не масштабируется:** команда из 3-5 человек обрабатывает 50-200 лотов/мес

---

## Решение: 6 AI-агентов

| # | Агент | Задача | LLM-вызовы |
|---|-------|--------|------------|
| 1 | **Planner** | Парсинг заявки → категория, позиции, сроки, бюджет | 1 |
| 2 | **Sourcer** | Поиск поставщиков: Qdrant-индекс + веб-скрейпинг | 0–1 |
| 3 | **Communicator** | Генерация RFQ-писем, отправка по SMTP | 1 |
| 4 | **Negotiator** | Анализ КП, торги по цене/срокам | 1–2 |
| 5 | **Verifier** | Cross-check другой LLM (anti-hallucination) | 1 |
| 6 | **Reporter** | Формирование отчёта: top-3, экономия, обоснование | 1 |

**Двойная верификация:** результат основного LLM проверяется независимой моделью для защиты от галлюцинаций.

---

## Технологический стек

| Слой | Технология | Зачем |
|------|-----------|-------|
| **AI/ML** | LangGraph + LangChain | Граф из 6 специализированных агентов |
| **LLM** | YandexGPT 5 Pro / GigaChat 2 Pro / Llama 3.3 70B | Мультимодельный роутер с fallback |
| **Backend** | FastAPI (async) + SQLAlchemy 2.x | REST API + WebSocket |
| **Frontend** | React 19 + TypeScript + Vite + Tailwind CSS 4 | SPA для buyers/admins |
| **Vector DB** | Qdrant | Семантический поиск по НСИ и поставщикам |
| **RDBMS** | PostgreSQL 16 | Лоты, пользователи, аудит |
| **Queue** | Celery + Redis | Фоновая обработка лотов |
| **Email** | SMTP/IMAP | Автоматическая отправка RFQ и приём ответов |
| **Monitoring** | Prometheus + Grafana + Sentry | Observability |
| **Auth** | JWT + bcrypt + OAuth2 (PKCE) + SAML 2.0 | Enterprise SSO |
| **Bot** | Telegram (@SnabAgent_Bot) | Уведомления + команды через мессенджер |
| **Deploy** | Vercel (frontend) + VPS + systemd + Docker | Продакшн-деплой |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                   │
│   React 19 + Vite + Tailwind · Dashboard · Lots · Analytics         │
│   Deployed: snab-agent.vercel.app (HTTPS)                           │
│   API proxy: Vercel rewrites → VPS backend (решает Mixed Content)   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ REST / WebSocket (через Vercel proxy)
┌────────────────────────────────▼────────────────────────────────────┐
│                       FastAPI Backend                                │
│  Routes: auth, lots, webhooks, SSO(OAuth2/SAML) · Rate Limiting     │
│  Deployed: 185.192.23.161:8000 (systemd service)                    │
└───────┬──────────────┬─────────────────┬──────────────┬─────────────┘
        │              │                 │              │
        ▼              ▼                 ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │  Qdrant  │ │    Redis     │ │   Email      │
│  (lots, auth,│ │  (NSI,   │ │  (Celery,   │ │  (SMTP+IMAP) │
│   audit)     │ │ suppliers)│ │   cache)    │ │  RFQ/ответы  │
└──────────────┘ └──────────┘ └──────────────┘ └──────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              ┌──────────┐   ┌──────────┐    ┌──────────┐
              │  Worker  │   │ Telegram │    │ LangGraph│
              │ (Celery) │   │   Bot    │    │ Pipeline │
              └──────────┘   └──────────┘    └──────────┘
```

---

## Пайплайн обработки лота

```
draft → planned → sourcing → rfq_sent → responses_collected
  → negotiating → verified → report_ready → [approved | rejected | escalated]
```

**Эскалация** (человеку) при:
- Уверенность Verifier < 70%
- Нарушение регуляторных ограничений (44-ФЗ, 223-ФЗ)
- Превышение бюджета > 15%
- Таймаут ответов от поставщиков

---

## API эндпоинты

### Публичные
| Метод | Путь | Назначение |
|-------|------|-----------|
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/login` | Авторизация (JWT) + демо-доступ |
| GET | `/api/v1/auth/verify-email` | Верификация email |
| GET | `/health` | Healthcheck |

### Защищённые (JWT / API-Key)
| Метод | Путь | Назначение |
|-------|------|-----------|
| GET | `/api/v1/lots` | Список лотов (пагинация, фильтры) |
| POST | `/api/v1/lots` | Создать лот |
| GET | `/api/v1/lots/{id}` | Детали лота |
| POST | `/api/v1/lots/{id}/approve` | Одобрить |
| POST | `/api/v1/lots/import-excel` | Импорт из Excel |
| WS | `/ws/lots/{id}` | Realtime обновления |
| POST | `/webhooks/telegram` | Telegram bot webhook |

### Telegram-бот команды
| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкции |
| `/new <описание>` | Создать новую заявку |
| `/status` | Текущие лоты и статусы |
| `/lot <id>` | Детали конкретного лота |
| `/approve <id>` | Одобрить лот |
| `/escalate <id>` | Эскалация на человека |
| `/help` | Справка по командам |

---

## Безопасность

- **Аутентификация:** JWT (access 15 мин + refresh 7 дней) + OAuth2 PKCE + SAML 2.0
- **Авторизация:** RBAC (admin, buyer, viewer) + customer_id isolation
- **Multi-tenancy:** Row-Level Security — каждый клиент видит только свои данные
- **PII-маскирование:** ИНН, ОГРН, email, телефоны маскируются перед отправкой в LLM
- **Rate limiting:** per-endpoint, IP-based
- **Пароли:** bcrypt, политика (8+ символов, цифра, спецсимвол)
- **Mixed Content:** решён через Vercel rewrites proxy (фронтенд HTTPS → бэкенд HTTP)

---

## Демо-доступ

Продукт включает встроенный демо-режим:
- **URL:** https://snab-agent.vercel.app/login?demo=true
- **Email:** demo@snabagent.ru
- **Пароль:** Demo123!@#
- При первом входе автоматически создаётся демо-пользователь с 5 примерами лотов
- Лоты показывают разные статусы пайплайна (sourcing, negotiating, verified, report_ready, approved)

---

## Структура проекта

```
snabagent/
├── src/snabagent/           # Backend (7800+ строк Python)
│   ├── agents/              # 6 LangGraph-агентов
│   ├── api/                 # FastAPI routes + SSO
│   │   ├── routes/          # lots, auth, webhooks
│   │   └── sso/             # OAuth2, SAML
│   ├── bot/                 # Telegram bot (polling + webhook)
│   ├── db/                  # SQLAlchemy models, repos, migrations
│   ├── email_service/       # SMTP sender, IMAP poller
│   ├── llm/                 # Router, YandexGPT, GigaChat, Fake
│   ├── parsers/             # PDF, DOCX, Excel parsers
│   ├── services/            # Metering, embeddings
│   ├── tasks/               # Celery tasks
│   └── ui/                  # Streamlit dashboard
├── frontend/                # React 19 + TypeScript + Vite
│   ├── public/logo.png      # Брендовый логотип
│   ├── vercel.json          # Vercel rewrites (API proxy)
│   └── src/pages/           # Landing, Dashboard, Lots, Login, etc.
├── tests/                   # 238 тестов
├── alembic/                 # Database migrations
├── deploy/                  # Caddy configs
├── docker-compose.yml       # Dev environment
├── docker-compose.server.yml # Production deployment
├── Dockerfile               # Multi-stage build
├── ROADMAP.md               # План развития после TechLab
├── PRESENTATION_PROMPT.md   # Промпт для презентации
└── requirements.lock        # Locked dependencies
```

---

## Деплой

| Компонент | URL | Провайдер | Статус |
|-----------|-----|-----------|--------|
| Frontend | https://snab-agent.vercel.app | Vercel | Работает |
| Backend API | http://185.192.23.161:8000 | VPS (systemd) | Работает |
| Telegram Bot | @SnabAgent_Bot | VPS (systemd) | Работает |
| Healthcheck | http://185.192.23.161:8000/health | VPS | OK |

---

## Ключевые метрики

| Метрика | Значение |
|---------|----------|
| Время обработки лота | 15 минут (vs 3-5 дней) |
| Экономия на закупках | 8-30% |
| AI-агентов в пайплайне | 6 |
| Покрытие тестами | 81% (238 тестов) |
| Поддерживаемые LLM | GigaChat, YandexGPT, Llama, OpenAI |
| SKU в месяц | 10 000+ |

---

## Конкурентные преимущества

| Критерий | SnabAgent | SAP Ariba | 1С:Закупки |
|----------|-----------|-----------|------------|
| AI-агенты | 6 (LangGraph) | Нет | Нет |
| Время старта | 5 минут | 6-12 месяцев | 2-4 месяца |
| Российские LLM | GigaChat + YandexGPT | Нет | Нет |
| Стоимость | От 0 ₽ (пилот) | $$$$$  | $$$ |
| Anti-hallucination | Двойная верификация | — | — |

---

## Контакты

- **Сайт:** https://snab-agent.vercel.app
- **Демо:** https://snab-agent.vercel.app/login?demo=true
- **Email:** scaleblinkk@vk.com
- **Telegram:** @SnabAgent_Bot
- **API:** http://185.192.23.161:8000/health

---

*Версия: 2.2.0 | Обновлено: Июнь 2026*
