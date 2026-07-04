# Communicator — карточка промпта

## Цель
Отправить персональный RFQ каждому поставщику и собрать ответы.

## Шаблон письма
`src/snabagent/agents/prompts/communicator_rfq.j2`.

Особенности:
- Subject: `[SnabAgent #LOT-{lot_short_id}] Запрос КП: {category_human}`
- Reply-To: `lot+{lot_id}@demo.snabagent.ru` (для маршрутизации входящих)
- В теле обязательно: список позиций (qty, unit, lead-time, gost), формат ответа, deadline, оговорка что письмо автоматическое.

## Парсинг ответов
`agents/tools/pdf_extractor.py:parse_offer_from_path` — LLM-парсер с JSON-схемой Offer.

В DEMO_MODE — `communicator._synthetic_offer()` детерминированно генерирует ответ от ~66 % поставщиков с разбросом цены 0.85–1.10 × typical_price.

## Защита
- Никаких реальных писем в dev (assert: `settings.smtp_host in ('mailhog', 'localhost', ...)`).
- Идемпотентность через `message_id` в `rfq_emails.message_id` (UNIQUE).
