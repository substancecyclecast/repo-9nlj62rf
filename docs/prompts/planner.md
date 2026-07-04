# Planner — карточка промпта

## Цель
Извлечь из «грязного» внутреннего запроса заказчика структурированный список позиций и сопоставить каждую с НСИ.

## Системный промпт
См. `src/snabagent/agents/prompts/planner_system.j2`.

Ключевые правила:
1. ⚠ **Никогда не выдумывать SKU.** Только из переданных кандидатов.
2. Если не найдено — `matched_nsi_sku=null`, `alternatives=[]`.
3. `confidence ∈ [0, 1]`, `overall_confidence < 0.65 ⇒ escalation_needed=true`.
4. Категория ОБЯЗАТЕЛЬНА из `mro|it|consumables|metals|chemistry|services`.
5. Только JSON. Без markdown.

## Контекст в user-prompt
- Сырой запрос
- Имя заказчика
- Текущая фаза (`pre_nmck`/`unregulated`/`post_tender_published`)
- Список фраз и top-5 кандидатов НСИ из векторного поиска (similarity ∈ [0,1])

## Выход
```json
{
  "items": [{"raw_phrase":..., "matched_nsi_sku":..., "qty":..., "unit":..., "confidence":..., "alternatives":[...]}],
  "category": "metals",
  "overall_confidence": 0.84,
  "escalation_needed": false,
  "escalation_reason": null
}
```

## Защита от галлюцинаций
- Планировщик НЕ имеет доступа к интернету.
- НСИ-кандидаты приходят из Qdrant; matched_nsi_sku валидируется по списку SKU в audit_log (см. tests/integration/test_planner.py).
- Если LLM вернул SKU не из кандидатов — Planner откатит matched_nsi_sku в null и пометит low confidence.

## Метрика качества
- top-1 accuracy ≥ 85 % на синтетике из `docs/demo_scenarios.md`.
- hallucinated SKU == 0 на 100 запусках.
