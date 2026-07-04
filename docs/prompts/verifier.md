# Verifier — карточка промпта

## Цель
Независимая проверка каждого КП. Цена / срок / ГОСТ / реквизиты.

## Критически важное правило
Verifier **обязан** использовать LLM, отличную от primary. См. `complete_with_fallback(role='verifier')` — это разные провайдеры в `LLM_PRIMARY` vs `LLM_VERIFIER`.

Цель — поймать собственные галлюцинации primary-агента.

## Проверки
1. INN / OGRN валидны (через `spark_mock.check_inn_ogrn`).
2. SKU из КП совпадают с НСИ.
3. lead_time <= требуемого.
4. ГОСТ совпадает.
5. Валюта = RUB.
6. Отклонение цены от `typical_price` < 30 %.

## Скор уверенности
`confidence = max(0, 1 - 0.3 * high - 0.1 * medium)`.

`recommendation`:
- ≥ 0.7 → `approve`
- 0.4–0.7 → `escalate_to_human`
- < 0.4 → `reject`

## Промпт
См. `src/snabagent/agents/prompts/verifier_check.j2`.
