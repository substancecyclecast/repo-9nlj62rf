# Демо-сценарии

Все сценарии проигрываются на одном и том же `docker compose up -d` либо в полностью оффлайн-режиме (FakeLLM + SQLite + In-Memory Qdrant). Время до показа Top-3 в FakeLLM-режиме: 2-5 секунд, в prod-LLM: 6-10 минут.

## Сценарий 1. Металлопрокат (золотой путь)

**ТЗ:** `data/sample_tz/tz_metal_dirty.txt`
```
Срочно нужно металла на стройку, как обычно.
- Швелер 14-й, трешка, тонн 10 надо, как в прошлый раз брали у Северстали или аналог
- Арматура А500 диаметром 12, тонн 5
- Листы 3мм 09Г2С, тонн 8, к среде если можно
```

**Ожидаемый результат Planner:**

| raw_phrase | matched_nsi_sku | qty | unit | conf |
|---|---|---:|---|---:|
| Швелер 14-й, трешка, тонн 10 | MET-SHV-14-3PS | 10 | т | ≥0.85 |
| Арматура А500 диаметром 12, тонн 5 | MET-ARM-A500C-12 | 5 | т | ≥0.85 |
| Листы 3мм 09Г2С, тонн 8 | MET-LIST-3-09Г2С | 8 | т | ≥0.85 |

**Sourcer:** возвращает 6 поставщиков, из которых 3 — `historical` (Северсталь-Метиз, Мечел-Сервис, ММК Профиль).

**Communicator:** в DEMO_MODE синтезирует ответы от 4 поставщиков (66 % response rate).

**Verifier:** один из синтетических ответов имеет lead_time=45 дней (выше запрошенных 30) — Verifier ловит несоответствие.

**Reporter:** Top-3 с экономией ~8–12 % vs typical_price из НСИ.

**Запуск:**
```bash
# Через UI:  Streamlit → ➕ Новый лот → вставить ТЗ → ▶ Запустить
# Через API:
curl -sX POST http://localhost:8000/lots \
  -H 'Content-Type: application/json' \
  -d @<(jq -Rn '{customer_name:"SIBUR Demo", phase:"pre_nmck", raw_request: (input | @json)}' \
        < data/sample_tz/tz_metal_dirty.txt)
```

## Сценарий 2. ИТ-закупка

**ТЗ:** `data/sample_tz/tz_it_dirty.txt`
```
Нужно подобрать в офис на Бакунинской 15 ноутов для разработчиков.
Желательно леновки (T14 какие-нибудь, новые), 16 гигов оперативки …
Сюда же нужен один свич Cisco 9300 48 портов, но можно и аналог Eltex MES.
```

**Ожидаемый Planner:**

| raw_phrase | matched_nsi_sku | conf |
|---|---|---:|
| Леновки T14, 16 GB | IT-LP-LENOVO-T14 | ≥0.85 |
| Cisco 9300 48 портов | IT-SW-CISCO-9300 | ≥0.85 |

**Sourcer:** 5 ИТ-дистрибуторов (Софтлайн, Мерлион + 3 синтетических из spark_mock).

**Verifier:** ловит, если synthetic offer указывает «Gen 3» при ожиданиях Gen 4 (см. NSI-атрибуты Lenovo T14 Gen 4).

**Reporter:** Top-3 с экономией ~5–10 %.

## Сценарий 3. Химия (эскалация)

**ТЗ:** `data/sample_tz/tz_chemistry_dirty.txt`
```
1) ПЭВД марки 273 или аналог LDPE — 25 тонн
2) Стабилизатор аналог Irganox 1010 — 200 кг
3) Краситель сажа техническая — 1 тонна
```

**Ожидаемый Planner:**

| raw_phrase | matched_nsi_sku | conf |
|---|---|---:|
| ПЭВД марки 273 | CHEM-PE-HDPE-273 | ≥0.85 |
| Irganox 1010 | CHEM-STAB-IRGAFOS-168 (alternative) | 0.45–0.6 |
| сажа техническая | CHEM-COLOR-CARBON-N220 | ≥0.75 |

**Эскалация:** overall_confidence может оказаться < 0.65 из-за Irganox → Planner ставит `escalation_needed=true`, посылает `{severity:"medium"}` в n8n → Telegram.

В UI Streamlit лот отображается с жёлтым плашком «⚠ Эскалация: Низкая уверенность маппинга НСИ».

## Smoke-test чек-лист демо

- [ ] `make offline-demo` отрабатывает за < 30 с и пишет `data/offline_demo_results.json` со статусами `report_ready` для metals/it и `report_ready|escalated` для chemistry.
- [ ] В Streamlit для лота metals видно audit-tree с ≥ 5 шагами (planner → sourcer → communicator → verifier → reporter).
- [ ] Аудит-карточка планера содержит вкладки Input/Output/Prompt/Raw LLM/Meta.
- [ ] Кнопка `Approve Top-1` меняет статус на `approved` и публикует WS-сообщение.
- [ ] n8n workflow `escalation` импортируется без ошибок (`POST :5678/rest/workflows/import` или через UI).
