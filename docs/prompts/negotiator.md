# Negotiator — карточка промпта

## Цель
Один раунд переговоров с поставщиками: попросить скидку до уровня «между min-price и текущей».

## Регуляторный фильтр (223-ФЗ)
`src/snabagent/agents/tools/regulatory_filter.py`. Блокирует, если:
1. `phase == "post_tender_published"` — нельзя переписываться о ценах после публикации.
2. `category` не из `regulatory_allowed_categories` (mro/it/consumables/services/spot_metals/metals/chemistry).
3. `phase == "unregulated" AND total_estimated_rub > 1_000_000`.

Если заблокировано — Negotiator-нод пишет в audit_log step `regulatory_block` и пропускает.

## Шаблон письма
`src/snabagent/agents/prompts/negotiator_request.j2`.

Параметры: `target_price_rub`, `your_price_rub`, `desired_lead_time`, `reply_deadline_hours`.

## Защита
- Только **один** раунд. После него — переход к Verifier.
- Никогда не уговаривать на скидку > 20 % (риск signal-fail в audit / 223-ФЗ).
