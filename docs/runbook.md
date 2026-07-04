# Runbook

## Регулярные операции

### Бэкап БД (раз в день)
```bash
docker compose exec -T postgres pg_dump -U snab snabagent | gzip > /opt/snabagent/backups/snabagent_$(date +%F).sql.gz
```

### Бэкап Qdrant
```bash
docker compose exec -T qdrant tar czf - /qdrant/storage > /opt/snabagent/backups/qdrant_$(date +%F).tar.gz
```

### Ротация .eml-дампов
Если SMTP недоступен, sender пишет в `data/sent_emails/*.eml`. Чистим раз в неделю:
```bash
find /opt/snabagent/data/sent_emails -mtime +7 -delete
```

## Алерты

| Событие | Сигнал | Что делать |
|---|---|---|
| Лот в `escalated` | Telegram бот | Проверить `escalation_reason` в Streamlit |
| `report_ready` доля < 80 % за час | Метрика | Смотреть audit_log по `confidence` |
| Verifier `confidence_score` p95 < 0.5 | Метрика | Проверить, не сменился ли formati ответа поставщиков |
| Qdrant `/healthz` != 200 | Caddy log | `docker compose restart qdrant` |
| Postgres conn pool exhausted | structlog | Увеличить `pool_size` в DSN |

## Recovery сценарии

### Лот завис в `sourcing`
```python
# В контейнере api
docker compose exec api python scripts/replay_lot.py <lot_id>
```

### Все эмбеддинги в Qdrant потерялись
```bash
docker compose exec api python scripts/seed_qdrant.py
```

### MailHog недоступен
Письма не теряются — sender фолбэчит в `data/sent_emails/*.eml`. Восстановить SMTP и при необходимости вручную перетранслировать дампы.

### Хотим переключить LLM на лету
```bash
# В /opt/snabagent/.env
LLM_PRIMARY=gigachat   # был yandex
docker compose restart api worker
```

## SLA для пилота (рекомендуем заказчику)

- Доступность API/UI: 99 % (15 минут даунтайма в день)
- Время отклика на лот < 12 минут (p95)
- RTO 4 ч, RPO 24 ч (ежедневный бэкап БД и Qdrant)

## Контакт

Внутренний дежурный — Telegram-бот `@snabagent_founder` (заменить на реальный handle при пилоте).
