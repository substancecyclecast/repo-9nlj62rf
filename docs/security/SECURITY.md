# SnabAgent — Security Policy

**Версия 1.0 от 01.01.2026**

## 1. Угрозы и контрмеры

| Угроза | Контрмера в SnabAgent |
|---|---|
| Unauthorized access | JWT (24 ч) + bcrypt 12 раундов + RBAC (admin/buyer/viewer) |
| Cross-tenant data leak | `Principal.filter_customer_id()` во всех routes + БД-индексы |
| Brute-force паролей | Rate-limit на /auth/login (планируется через slowapi) + 401 при неверном пароле |
| PII в логах | `audit/logger.py` маскирует ФИО, телефоны, email перед записью |
| SQL-injection | SQLAlchemy ORM — параметризованные запросы; нет raw SQL |
| XSS в Streamlit | Streamlit рендерит как text-only; HTML только через `unsafe_allow_html=True` в нашем коде с фиксированным CSS |
| CSRF | API использует только JSON-тело (не form-data); JWT в Authorization-заголовке |
| File upload attacks | Лимит 10 МБ, проверка расширений, `tempfile` с unique-suffix |
| LLM prompt injection | Все промпты содержат фиксированный системный заголовок; пользовательский ввод заключён в delimiter-маркеры |
| Замена/манипуляция audit-log | append-only таблица, ON DELETE RESTRICT, не редактируется ни одним endpoint |
| Secret leak в Git | .gitignore включает .env, .env.local, credentials.json, *.key, *.pem |
| Token leak в логах | API-key и JWT не логируются (запретные ключи в `audit/logger.py`) |
| Insecure deserialization | JSON через Pydantic с strict validation; нет pickle |

## 2. Аутентификация и авторизация

### 2.1. Аутентификация

- **Пароли**: bcrypt 12 раундов, truncate 72 байта (стандарт bcrypt).
- **JWT**: HS256, expires 24 ч, refresh механизм отсутствует (для production — добавить).
- **API-ключ**: используется только в dev-окружении (`X-API-Key`); в production — отключается через переменную `API_KEY=disabled`.

### 2.2. Авторизация

Роли:
- **admin**: полный доступ, создание пользователей, изменение настроек, утверждение лотов >5 млн ₽.
- **buyer**: создание/просмотр лотов своей компании, утверждение до 5 млн ₽ (по `approval_limit_rub`).
- **viewer**: только просмотр.

Multi-tenant изоляция реализована через `Principal.filter_customer_id()`:
```python
# Если admin — все клиенты, если buyer/viewer — только свой customer_id
def filter_customer_id(self, customer_id: UUID | None) -> UUID | None:
    if self.role == "admin":
        return customer_id  # фильтр опциональный
    return self.customer_id  # фильтр форсированный
```

## 3. Защита данных

### 3.1. Маскинг PII

В `audit/logger.py`:
- Телефон `+79161234567` → `+7916***4567`
- Email `ivan@company.ru` → `i***@company.ru`
- ФИО «Иванов Иван Иванович» → `И***ов И.И.`

### 3.2. Шифрование

- **TLS 1.3** для всех HTTP/WebSocket (Caddy reverse-proxy).
- **AES-256** для БД (PostgreSQL TDE через Yandex Cloud / on-prem).
- **bcrypt** для паролей (12 раундов).

### 3.3. Резервное копирование

- Ежедневное полное копирование БД.
- 30-дневное хранение копий.
- Тестирование восстановления раз в квартал.

## 4. Аудит и логирование

### 4.1. Audit-log

Все действия пользователей логируются:
- кто (user_id, email, role, IP);
- что (endpoint, lot_id, action);
- когда (timestamp UTC);
- результат (status_code, error если есть).

Audit-log:
- **Append-only**: нет UPDATE/DELETE endpoint.
- **Хранение**: 5 лет.
- **Маскинг**: все PII маскируются перед записью.

### 4.2. Мониторинг

- **Prometheus**: `/metrics` endpoint.
- **Grafana**: dashboard `docs/dashboards/snabagent-prod.json`.
- **Алерты**: высокая частота 5xx, латентность p95 >2s, эскалации без обработки.

## 5. Уязвимости и инциденты

### 5.1. Reporting

Сообщения о уязвимостях: **security@snabagent.example** (PGP-ключ публикуется на сайте).

Reward: **до 100 000 ₽** за critical/high уязвимости (по согласованию).

### 5.2. Response

- **Critical**: исправление в течение 24 часов, уведомление клиентам в течение 12 часов.
- **High**: исправление в течение 7 дней.
- **Medium**: исправление в следующем релизе (до 30 дней).
- **Low**: исправление по графику.

## 6. Сертификация и соответствие

### 6.1. Текущие

- **ФЗ № 152**: соответствие через маскинг PII, хранение в РФ, audit-log.
- **ФЗ № 44 / № 223**: полный audit-trail для гос. закупок.

### 6.2. В работе

- **ISO 27001**: пилотный аудит Q2 2026.
- **ФСТЭК (сертификация СрЗИ)**: подача документов Q3 2026.
- **GDPR**: рассмотрение для экспансии на EAEU (Q4 2026).

## 7. Security scanning

### 7.1. CI/CD

- **bandit**: статический анализ Python-кода на уязвимости (включён в Makefile).
- **safety**: проверка зависимостей на известные CVE.
- **pip-audit**: проверка pip-пакетов на CVE (`make security`).
- **semgrep**: расширенный SAST для security patterns.

### 7.2. Запуск локально

```bash
make security
# или вручную:
bandit -r src/
safety check
pip-audit
semgrep --config=auto src/
```

См. `docs/security/scan_results.md` для последних результатов.

## 8. Patch management

- Обновление зависимостей (`pip install -U`): раз в 2 недели.
- Применение security patches: в течение 7 дней после публикации.
- Major upgrade Python: раз в год (с тестированием).

## 9. Backup и Disaster Recovery

- **RPO** (Recovery Point Objective): 1 час для Enterprise, 24 часа для Pro/Pilot.
- **RTO** (Recovery Time Objective): 1 час для Enterprise, 4 часа для Pro/Pilot.
- **DR-тестирование**: раз в полугодие.

## 10. Контакты

- **Security team**: security@snabagent.example
- **General**: contact@snabagent.example
- **PGP**: https://snabagent.example/pgp.asc

---

**Hall of Fame** — благодарности исследователям безопасности будут публиковаться по мере появления.
