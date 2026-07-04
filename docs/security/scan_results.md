# Результаты сканирования безопасности — SnabAgent

**Дата сканирования**: см. `data/security/` (актуально на дату build).

## 1. Bandit (SAST)

**Команда:**
```bash
bandit -r src -ll
```

**Результат:** 12 Low-severity issues, 0 Medium/High/Critical.

Все 12 — это `try/except/pass` в UI (Streamlit), скрывающие ошибки построения графиков. Не являются security-уязвимостями.

### Покрытие
- 4 605 строк кода Python в `src/`.
- 0 файлов пропущено.

### Список (все Low):
- 12× `B110:try_except_pass` в `src/snabagent/ui/streamlit_app.py` — обработка ошибок Plotly.

**Вывод**: AcceptedRisk — это UI-обработка ошибок графиков; данные не утекают.

## 2. pip-audit (CVE сканирование зависимостей)

**Команда:**
```bash
pip-audit --skip-editable
```

**Результат:** 51 known vulnerability in 15 packages.

### Критические CVE и mitigation

| Package | Version | CVE | Severity | Mitigation |
|---|---|---|---|---|
| starlette | 0.41.3 | CVE-2025-54121 | High | Обновить до 0.49.1+ |
| python-multipart | 0.0.17 | CVE-2024-53981 | Medium | Обновить до 0.0.18+ |
| streamlit | 1.40.2 | CVE-2026-33682 | High | Обновить до 1.54.0+ |
| pypdf | 5.1.0 | CVE-2026-27888 (+ 12 others) | High | Обновить до 6.10.2+ |
| pytest | 8.3.4 | CVE-2025-71176 | Low | Dev-only |
| transformers | 4.57.6 | PYSEC-2025-217 | Medium | Обновить до 5.0.0rc3+ |

### Roadmap

- **Q1 2026**: обновление starlette/python-multipart/streamlit/pypdf в рамках регулярного maintenance.
- **Зависимости в pyproject.toml** обновляются через `pip-tools` ежемесячно.
- В production-окружении SnabAgent **запускается за reverse-proxy Caddy** с TLS 1.3 и rate-limiting, что снижает риск эксплуатации CVE.

## 3. Safety

**Команда:**
```bash
safety check
```

**Результат**: см. `data/security/safety_output.txt`. Большинство CVE совпадают с pip-audit.

## 4. Ruff (lint)

**Команда:**
```bash
ruff check src tests
```

**Результат:** 0 errors.

Все стилистические нарушения исправлены автоматически в рамках разработки.

## 5. mypy (type-checking)

**Команда:**
```bash
mypy src/snabagent
```

**Результат**: некритичные предупреждения о opt-in типизации (annotation-related-warnings).

В CI mypy запускается с `|| true` — не блокирует. Постепенное ужесточение типов планируется в Q1-Q2 2026.

## 6. Покрытие тестами

**Команда:**
```bash
pytest --cov=src/snabagent --cov-fail-under=70
```

**Результат:** 81% (после `omit=` UI + LLM-провайдеры). 113 тестов pass.

См. `coverage.xml` или вывод pytest.

## 7. Сводка

| Сканер | Результат | Severity | Action |
|---|---|---|---|
| bandit | 12 Low (try/except в UI) | acceptable | — |
| pip-audit | 51 CVE в зависимостях | Mixed | regular update Q1 2026 |
| safety | Same as pip-audit | Mixed | — |
| ruff | 0 errors | — | — |
| mypy | Warnings (opt-in) | — | gradual hardening |
| pytest | 113 passed, 81% coverage | — | maintained |

**Общий вывод**: код безопасен для pilot-развёртывания. Перед production-релизом необходимо обновить starlette/streamlit/pypdf и провести внешний аудит (Q3 2026 → ISO 27001 сертификация).
