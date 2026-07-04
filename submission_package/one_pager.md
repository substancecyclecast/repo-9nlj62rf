# SnabAgent — One-pager

## Проблема
Снабженцы крупных промышленных холдингов ежедневно вручную обрабатывают сотни «грязных» внутренних заявок, рассылают RFQ по поставщикам, сводят КП в Excel. Цикл «заявка → 3 КП → выбор» — **3–15 рабочих дней**. На этапе НМЦК теряется до 5–10 % бюджета из-за неоптимального выбора и человеческой ошибки.

## Решение
SnabAgent — мульти-агентный LLM-сервис, сокращающий цикл «заявка → 3 КП» с **3–15 дней до 30–60 секунд** (1 секунды в demo-режиме на FakeLLM).
6 специализированных агентов (Planner → Sourcer → Communicator → Negotiator → Verifier → Reporter) на LangGraph, независимая верификация другой LLM, полный audit-log на 5 лет.

## Ключевые отличия
- **Защита 44/223-ФЗ.** Регуляторный фильтр блокирует автокоммуникацию после публикации тендера, ограничение сумм, whitelist категорий.
- **Multi-LLM с fallback.** YandexGPT 5 Pro + GigaChat 2 Pro primary/fallback, Llama 3.3 для on-prem, FakeLLM для оффлайн-демо.
- **PII-маскинг 152-ФЗ.** ФИО, ИНН, телефоны и email маскируются в audit-log; OpenAI запрещён в production по умолчанию.
- **Multi-tenant + JWT-RBAC.** Полная изоляция данных по customer_id, роли admin/buyer/viewer, лимиты одобрения.
- **Российский стек.** Deploy на Yandex Cloud (Terraform + cloud-init), хранение данных в РФ.

## Метрики MVP (актуально)
- **113 тестов** проходят, **81%** покрытие.
- **Benchmark accuracy: 100 %** на 10 ground-truth сценариях.
- **p50 = 0.46 сек**, p95 = 0.78 сек в demo-режиме (FakeLLM).
- **MAE цены: 1.92 %** vs. эталонная середина диапазона.
- **Экономия 9–12 %** vs. среднерыночной цены на пилотных сценариях.

## Готовность
- ✔ Полный исходный код (FastAPI + LangGraph + Streamlit), Proprietary license.
- ✔ Docker-compose: postgres, qdrant, redis, mailhog, n8n, api, worker, streamlit.
- ✔ Terraform для Yandex Cloud (8 vCPU / 16 GB / 80 GB SSD).
- ✔ 3 демо-сценария (metals, IT, chemistry) играются < 30 сек.
- ✔ Prometheus `/metrics` + Grafana dashboard JSON (11 панелей).
- ✔ Юридические шаблоны: EULA, NDA, DPA, SLA, AUP.
- ✔ Чек-лист 152-ФЗ + ISO 27001 mapping.
- ✔ ROI-калькулятор HTML (`docs/sales/roi_calculator.html`).

## Целевой клиент
Крупная промышленная группа с собственной службой закупки (≥ 50 снабженцев, ≥ 5 000 заявок/мес.).
Сегмент: нефтехимия, металлургия, ритейл-логистика, госкорпорации с регулируемой 44/223-ФЗ закупкой.

## Бизнес-модель
- **SaaS**: от 150 тыс ₽/мес (Pilot) до 4.5 млн ₽/мес (Enterprise) — см. `docs/sales/pricing.md`.
- **On-prem**: 12 млн ₽ разово + 1.2 млн ₽/год support.
- **Trial**: 90 дн free.

## Финансы (3-летняя проекция)
- Год 1: ARR 51 млн ₽, окупаемость в мес 7.
- Год 2: ARR 144 млн ₽.
- Год 3: ARR 252 млн ₽, ROI инвестора 5x за 3 года.

## Ближайшие шаги (12 месяцев)
1. Pilot на 1 категории у 3 заказчиков (СИБУР, Северсталь, X-холдинг).
2. Интеграция с 1С УХ и СПАРК-Интерфакс.
3. Расширение НСИ до 50 000+ SKU + active learning.
4. ISO 27001 + сертификация ФСТЭК.

## Контакты
SnabAgent Team · `contact@snabagent.ru` · Telegram `@snabagent_founder`
Demo: https://demo.snabagent.example
