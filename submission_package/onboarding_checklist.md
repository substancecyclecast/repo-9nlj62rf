# Onboarding-чеклист для пилота

> Цель: за 2 недели прийти к стабильному автозапуску 1 категории закупок на стороне Заказчика.

## Неделя 0 — pre-kickoff

- [ ] Подписан NDA (`submission_package/nda_template.md`)
- [ ] Сформирована рабочая группа: 1 procurement-lead, 1 IT-владелец, 1 архитектор ИБ, 1 представитель снабжения.
- [ ] Выбрана пилотная категория (рекомендуем: MRO или metals — низкий регуляторный риск).
- [ ] Назначен ответственный за выгрузку НСИ.

## Неделя 1 — kickoff

- [ ] Доступ Заказчика на VM (Yandex Cloud, deploy/yc/terraform).
- [ ] Получены / выпущены ключи:
  - [ ] `LLM_YC_FOLDER_ID`, `LLM_YC_AUTH_TOKEN` (YandexGPT 5 Pro).
  - [ ] `LLM_GIGACHAT_AUTH_KEY` (GigaChat 2 Pro).
  - [ ] `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ESCALATION_CHAT_ID`.
  - [ ] (опционально) SMTP-креды Mailcow на subdomain `demo.<customer>.ru`.
- [ ] Сетевые правила: открыты 80/443; SSH — только из ИБ-VPN.
- [ ] Выгружена тестовая НСИ (200–2 000 SKU CSV).
- [ ] Выгружен список «доверенных» поставщиков (50–200).
- [ ] 10 «грязных» заявок прошлого месяца переданы как ground-truth.

## Неделя 2 — стабилизация

- [ ] `make dev` поднят на Yandex VM, открыт Streamlit за TLS (Caddy).
- [ ] Прогон 3 e2e-сценариев из spec → status `report_ready`.
- [ ] Прогон 10 ground-truth заявок → расчёт top-1 accuracy НСИ-маппинга.
- [ ] Подключён n8n с Telegram-эскалациями.
- [ ] Сделан snapshot БД и Qdrant (см. `docs/runbook.md`).

## Чеклист безопасности

- [ ] `.env` на VM имеет права 0600, владелец — non-root user.
- [ ] PostgreSQL не торчит наружу (firewall + pg_hba.conf).
- [ ] Qdrant закрыт API-ключом.
- [ ] Caddy: TLS A+ (заголовки HSTS, X-Content-Type-Options).
- [ ] structlog → отправка в Sentry (если есть DSN).

## Acceptance criteria пилота

| Метрика | Минимум | Цель |
|---|---|---|
| NSI top-1 accuracy | 75 % | 85 % |
| Pipeline p50 | 12 мин | 6 мин |
| Доля автоматически закрытых лотов | 50 % | 70 % |
| Экономия vs typical | 4 % | 7 % |

При достижении — переход на коммерческий контракт (см. `submission_package/financial_model.md`).
