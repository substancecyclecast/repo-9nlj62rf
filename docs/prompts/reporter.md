# Reporter — карточка промпта

## Цель
Сформировать финальный отчёт по лоту: Top-3 КП, экономия vs typical_price, обоснование.

## Правила сортировки
1. Confidence DESC (от Verifier).
2. Total_price ASC.

## Расчёт savings
```
typical_total = sum(item.qty * item.typical_price for item in parsed_items)
best_total    = top_1.offer.total_price
savings_rub   = max(0, typical_total - best_total)
savings_pct   = round(savings_rub / typical_total * 100, 2)
```

## Промпт
См. `src/snabagent/agents/prompts/reporter_summary.j2`.

Шаблон: 3-4 предложения, факты, без маркетинговых слов.

## Выход (final_report)
```json
{
  "summary": "Рекомендуется выбрать ...",
  "top_3": [
    {"supplier_name":..., "inn":..., "total_price_rub":..., "lead_time_days":..., "score":..., "discrepancies":[], "rationale":"...", "recommendation":"approve"}
  ],
  "savings_vs_avg_rub": 124000,
  "savings_vs_avg_pct": 9.2,
  "risk_flags": [...],
  "next_action": "send_to_human_for_approval",
  "human_review_required": true
}
```
