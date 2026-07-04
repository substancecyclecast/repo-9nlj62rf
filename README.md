# SnabAgent MVP

[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Автономный мульти-агентный сервис закупок: «грязная» заявка → 6 поставщиков → 3 коммерческих предложения → сравнительная таблица с обоснованием. Все решения логируются и аудируются.

---

## 🏆 Qwen Cloud Global AI Hackathon — «SnabAgent: Qwen-Powered Autopilot for Enterprise Procurement»

**Трек:** Autopilot Agent (+ MemoryAgent + Agent Society).
SnabAgent — это production-ready автопилот закупок: 8 агентов на LangGraph, независимый
верификатор на отдельной модели Qwen (анти-галлюцинации), долговременная память
(самообучение) и полный аудит-трейл. LLM — **Qwen Cloud (Alibaba DashScope)**, деплой — **Alibaba Cloud ECS**.

**Запуск на Qwen за 3 шага:**
```bash
cp .env.example .env
# в .env выставить:
#   LLM_PRIMARY=qwen   LLM_FALLBACK=qwen   LLM_VERIFIER=qwen   LLM_VERIFIER_FALLBACK=qwen
#   LLM_QWEN_API_KEY=sk-...   (ключ DashScope / Model Studio)
make dev            # или см. deploy/alibaba/ для ECS
```
- Провайдер Qwen: <src/snabagent/llm/qwen.py> (OpenAI-compatible, `dashscope-intl` endpoint).
- Разные модели для reasoning и верификатора: `qwen-max` (primary) vs `qwen-plus` (verifier) —
  анти-галлюцинационная гарантия сохраняется, роутер это проверяет на старте.
- Долговременная память (MemoryAgent): узлы `Memory Recall` / `Memory Writeback`,
  таблицы `company_profiles` / `supplier_memory` / `lot_decision_memory`.
- Деплой на Alibaba Cloud: <deploy/alibaba/> (ECS-гайд, docker-compose, architecture diagram, deploy.sh).

---

## Что внутри

| Слой | Стек |
|---|---|
| LLM-роутер | **Qwen Cloud (qwen-max / qwen-plus)** · YandexGPT 5 Pro · GigaChat 2 Pro · Llama 3.3 70B · GPT-4.1 (dev, с PII-masking) · **FakeLLM** для оффлайна |
| Граф агентов | LangGraph (Memory Recall → Planner → Sourcer → Communicator → Negotiator → Verifier → Reporter → Memory Writeback) |
| Память (MemoryAgent) | PostgreSQL: профиль компании, скоры надёжности поставщиков (EMA), история решений |
| API | FastAPI + WebSocket + Mailcow webhook |
| UI | Streamlit (аудит-tree, Top-3, Approve/Reject) |
| Хранилище | PostgreSQL 16 · Qdrant 1.12 · Redis 7 |
| Очередь | Celery + redis (worker + beat) |
| Почта | MailHog (dev) · Mailcow (prod) · IMAP-поллер |
| Скрейпинг | Playwright · SPARK-mock CSV |
| Эскалации | n8n workflows (Telegram/Slack) |
| Деплой | docker-compose · Caddy · Terraform для Yandex Cloud · cloud-init |

## 30-минутный quickstart

### Вариант A. Полностью оффлайн (без Postgres/Qdrant/LLM)

Требуется только Python 3.11+.

```bash
unzip snabagent.zip
cd snabagent
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev] aiosqlite
python scripts/run_offline_demo.py
```

Скрипт:
1. Сидит SQLite (`./snabagent_offline_demo.db`).
2. Создаёт коллекции в in-memory векторном хранилище.
3. Прогоняет 3 сценария (metals / it / chemistry) на FakeLLM.
4. Пишет `data/offline_demo_results.json`.

Ожидаемый вывод (выдержка):
```
- [metals]    status=report_ready items=3 suppliers=6 responses=4 verifications=4 savings=8-12%
- [it]        status=report_ready items=2 suppliers=5 responses=3 verifications=3 savings=5-10%
- [chemistry] status=report_ready items=3 suppliers=4 responses=3 verifications=3 savings=4-8%
```

Локальный Streamlit можно поднять отдельно (использует уже созданную базу):
```bash
DATABASE_URL=sqlite+aiosqlite:///./snabagent_offline_demo.db STREAMLIT_API_BASE=http://localhost:8000 \
  uvicorn snabagent.api.main:app --port 8000 &
streamlit run src/snabagent/ui/streamlit_app.py --server.port 8501
```

### Вариант B. Полный docker-compose (рекомендуется для пилота)

```bash
cp .env.example .env
# Заполнить LLM_PRIMARY=yandex|gigachat и креды, либо оставить LLM_PRIMARY=fake.
make dev
```

Запустит: postgres · qdrant · redis · mailhog · n8n · api · worker · streamlit.

- API: <http://localhost:8000/docs>
- Streamlit: <http://localhost:8501>
- MailHog UI: <http://localhost:8025>
- n8n: <http://localhost:5678> (admin / `N8N_ADMIN_PASS`)

### Вариант C. Yandex Cloud (production-ready)

```bash
cd deploy/yc/terraform
cp terraform.tfvars.example terraform.tfvars  # заполнить токены
terraform init && terraform apply
# Получаем external_ip
scp -r ../../../snabagent.zip ubuntu@<external_ip>:/opt/snabagent/
ssh ubuntu@<external_ip>
cd /opt/snabagent && unzip snabagent.zip
./deploy/yc/ansible/deploy_app.sh   # docker compose up -d + migrate + seed
```

Caddy в `deploy/caddy/Caddyfile` автоматически выпустит Let's Encrypt сертификат для `demo.snabagent.ru`.

## Архитектура

См. <docs/architecture.md>. Кратко:

```
                    ┌────────────┐
                    │  Streamlit │  ← пользователь
                    └─────┬──────┘
                          │ REST + WS
                    ┌─────▼──────┐
   webhook (Mailcow)│  FastAPI   │
   ─────────────────┤  /lots,    │
                    │  /audit,   │
                    │  /webhooks │
                    └─────┬──────┘
                          │ BackgroundTask / Celery
                  ┌───────▼────────┐
                  │   LangGraph    │
                  │  StateGraph    │
                  └─┬──┬──┬──┬──┬─┘
   memory_recall → planner sourcer communicator negotiator verifier reporter → memory_writeback
                          ↑   ↓                          ↑
                    [LLM router]                  [independent model]
                          │                              │
      Qwen (qwen-max) / Yandex / GigaChat / Llama    Qwen (qwen-plus)
                          │
                 Persistent memory (Postgres): profile · supplier reliability · past lots
```

Диаграмма высокого качества (Mermaid) с потоком Qwen → агенты → БД — в
<deploy/alibaba/architecture.md>. Подробности по каждому агенту — `docs/prompts/*.md`.
Все промпты также вынесены в `src/snabagent/agents/prompts/*.j2`.

## Промпты и решения

* Планировщик (`docs/prompts/planner.md`) — нулевая толерантность к выдуманным SKU.
* Соурсер (`docs/prompts/sourcer.md`) — три источника, weight (historical 0.5 / vector 0.3 / spark 0.2).
* Коммуникатор (`docs/prompts/communicator.md`) — RFQ-шаблоны (`agents/prompts/communicator_rfq.j2`).
* Переговорщик (`docs/prompts/negotiator.md`) — единственный раунд + `regulatory_filter`.
* Верификатор (`docs/prompts/verifier.md`) — обязан использовать ИНУЮ LLM-модель.
* Репортёр (`docs/prompts/reporter.md`) — Top-3 + savings vs typical.

## Демо-сценарии

Файл <docs/demo_scenarios.md> описывает 3 готовых проигрываемых сценария:
1. Металлопрокат: «Швелер 14-й, трешка» + арматура + листы → 6 поставщиков → Top-3 со скидкой 8–12%.
2. IT: Ноуты Lenovo + Cisco/Eltex → Верификатор ловит несоответствие модели Gen.
3. Химия: ПЭВД-273 + Irganox (отсутствует в НСИ) → graceful эскалация в n8n.

ТЗ-файлы лежат в `data/sample_tz/*.txt`, а также в `.docx` и `.pdf`.

## Тесты

```bash
make test                  # pytest + coverage, FakeLLM
pytest tests/unit          # 0.5 c
pytest tests/integration   # ~5 c
pytest tests/e2e           # ~30 c (3 сценария)
```

Текущий статус: **238 тестов, 72% покрытие, 0 ruff-ошибок**.

## Бенчмарк

```bash
make bench-strict          # 10 ground-truth сценариев, --min-accuracy 0.70
```

Текущий результат: **accuracy 100%**, p50 0.46s, p95 0.78s, MAE цены 1.92%.

JSON-отчёт сохраняется в `data/benchmark_results.json`.

## Метрики и наблюдаемость

- `GET /metrics` — Prometheus format (Counter/Gauge/Histogram).
- Grafana dashboard: `docs/dashboards/snabagent-prod.json`.
- `GET /health` — Liveness/Readiness.

## Multi-tenant + JWT

```bash
make seed-users            # создаст admin@sibur.demo / admin123, buyer@sibur.demo / buyer123, viewer@sibur.demo / viewer123

# Login:
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sibur.demo","password":"admin123"}'
# → {"access_token":"<JWT>", ...}

# Используем токен:
curl http://localhost:8000/auth/me -H "Authorization: Bearer <JWT>"
```

Роли:
- **admin**: полный доступ, создание пользователей, одобрение лотов.
- **buyer**: создание/просмотр лотов своей компании, одобрение до `approval_limit_rub`.
- **viewer**: только просмотр.

## Сертификации и соответствие

См. `docs/security/`:
- `SECURITY.md` — политика безопасности.
- `152fz_checklist.md` — соответствие 152-ФЗ (70% реализовано).
- `iso27001_mapping.md` — маппинг на ISO 27001:2022 (82% покрытие).
- `scan_results.md` — результаты bandit / pip-audit / ruff.

## Безопасность

* `.env` НЕ коммитится. `.env.example` без секретов.
* PII (ИНН, ОГРН, email, phone) маскируется перед отправкой в любую внешнюю LLM, включая Qwen Cloud (см. `src/snabagent/llm/pii_masker.py`).
* Логи — structlog JSON + PII-mask processor.
* В prod OpenAI запрещён по умолчанию (`LLM_ENABLE_OPENAI_IN_PROD=false`).

## Структура архива

```
snabagent/
  README.md                           # этот файл
  pyproject.toml                      # зависимости (uv / pip)
  Makefile                            # make dev/test/seed/lint
  docker-compose.yml                  # dev-стэк
  docker-compose.prod.yml             # prod overlay (Caddy)
  Dockerfile                          # многослойный образ
  .env.example                        # шаблон конфигурации
  .pre-commit-config.yaml             # ruff + detect-secrets
  alembic.ini, alembic/               # миграции
  data/                               # mock-данные (NSI, suppliers, sample TZ)
  docs/                               # архитектура, промпты, runbook
  n8n/workflows/                      # 3 готовых workflow JSON
  src/snabagent/                      # код пакета
  scripts/                            # seed_db, seed_qdrant, run_offline_demo, …
  submission_package/                 # one-pager, NDA, onboarding, financial model, slide outline
  tests/                              # unit / integration / e2e
  deploy/yc/                          # Terraform + cloud-init для Yandex Cloud
  deploy/caddy/Caddyfile              # reverse-proxy + TLS
```

## Лицензия

[MIT](LICENSE) © 2026 SnabAgent Team.
