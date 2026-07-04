# Sourcer — карточка промпта

## Цель
Собрать 6–10 поставщиков для категории лота из трёх источников и ранжировать через LLM.

## Источники
| Источник | Вес | Реализация |
|---|---:|---|
| Исторические закупки заказчика | 0.5 | `agents/tools/historical.py:lookup_by_skus` |
| Векторный поиск по карточкам поставщиков | 0.3 | `vector/supplier_index.py` + Qdrant |
| СПАРК-mock по ОКВЭД категории | 0.2 | `agents/tools/spark_mock.py:search_by_okved` |

## Дедупликация
По ИНН. Если поставщик встречается одновременно в historical+vector — historical побеждает.

## Промпт ранжирования
См. `src/snabagent/agents/prompts/sourcer_user.j2`.

Ключевые правила:
1. ⚠ Не добавлять поставщиков, которых нет в кандидатах.
2. score ∈ [0,1] с дробной частью.
3. reasoning — 1 короткое предложение.
4. Только JSON, поле `suppliers`.

## Выход
```json
{
  "suppliers": [
    {"supplier_id":..., "inn":..., "name":..., "contact_email":..., "source":"historical", "rank":1, "score":0.94, "reasoning":"..."}
  ]
}
```

## Web-scraper
Если у кандидата отсутствует `contact_email`, попытаться найти на сайте Playwright-ом (`agents/tools/web_scraper.py`). Timeout — 10 сек, headless chromium. В оффлайн-режиме (отсутствие Playwright) — возвращает None.
