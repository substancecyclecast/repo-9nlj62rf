# ISO 27001:2022 — Соответствие SnabAgent

Маппинг контролей Annex A на реализованные меры в SnabAgent.

## A.5. Organizational controls

| # | Control | Status | Реализация |
|---|---|---|---|
| 5.1 | Policies for information security | ✅ | `docs/security/SECURITY.md`, EULA, DPA |
| 5.2 | Information security roles | ⏳ | Назначение DPO при регистрации компании |
| 5.7 | Threat intelligence | ✅ | Pip-audit, safety, bandit в CI |
| 5.10 | Acceptable use | ✅ | `docs/legal/AUP.md` |
| 5.11 | Return of assets | ✅ | Auto-delete после расторжения договора |
| 5.12 | Classification of info | ✅ | DPA §2.2: категории данных |
| 5.13 | Labelling of info | ⏳ | Tagging в БД (планируется Q2 2026) |
| 5.14 | Information transfer | ✅ | TLS 1.3 для всех каналов |
| 5.15 | Access control | ✅ | JWT + RBAC + per-customer isolation |
| 5.16 | Identity management | ✅ | User table + email-уникальность |
| 5.17 | Authentication info | ✅ | bcrypt 12 раундов + JWT HS256 |
| 5.18 | Access rights | ✅ | RBAC: admin/buyer/viewer |
| 5.19 | Supplier relationships | ✅ | NDA для всех контрагентов |
| 5.20 | Addressing security in agreements | ✅ | DPA + SLA |
| 5.23 | Cloud services | ✅ | Yandex Cloud (РФ) для SaaS |
| 5.25 | Reporting events | ✅ | Audit log + Prometheus alerts |
| 5.26 | Response to incidents | ✅ | `docs/security/SECURITY.md` §5.2 |
| 5.30 | ICT readiness for continuity | ✅ | Backup + DR plan |
| 5.34 | Privacy and PII protection | ✅ | PII-маскинг, 152-ФЗ соответствие |
| 5.35 | Independent review | ⏳ | Внешний аудит Q3 2026 |

## A.6. People controls

| # | Control | Status | Реализация |
|---|---|---|---|
| 6.1 | Screening | ⏳ | Проверка сотрудников при найме |
| 6.2 | Terms and conditions of employment | ✅ | Стандартный TK РФ + NDA |
| 6.3 | Awareness, education and training | ⏳ | Программа обучения IT-безопасности |
| 6.4 | Disciplinary process | ✅ | TK РФ |
| 6.5 | Remote working | ⏳ | Регламент удалённой работы |
| 6.7 | Confidentiality agreements | ✅ | NDA для всех сотрудников |

## A.7. Physical controls

| # | Control | Status | Реализация |
|---|---|---|---|
| 7.1 | Physical security perimeter | ✅ | Yandex Cloud / on-prem ЦОД клиента |
| 7.4 | Physical security monitoring | ✅ | Yandex Cloud мониторинг |
| 7.9 | Security of assets off-premises | ⏳ | Регламент для ноутбуков сотрудников |
| 7.10 | Storage media | ✅ | Шифрование БД, нет физических носителей |

## A.8. Technological controls

| # | Control | Status | Реализация |
|---|---|---|---|
| 8.1 | User endpoint devices | ⏳ | MDM для рабочих ноутбуков (планируется) |
| 8.2 | Privileged access rights | ✅ | admin-роль, аудит привилегированных действий |
| 8.3 | Information access restriction | ✅ | per-customer фильтрация |
| 8.4 | Access to source code | ✅ | Private repo + RBAC GitHub/GitLab |
| 8.5 | Secure authentication | ✅ | JWT + bcrypt; password policy в `User.password` validator |
| 8.6 | Capacity management | ✅ | Prometheus mon, autoscaling в k8s |
| 8.7 | Protection against malware | ✅ | Лимит файлов, расширения, тестирование вирусами в pilot |
| 8.8 | Management of technical vulnerabilities | ✅ | pip-audit, bandit, safety в CI |
| 8.9 | Configuration management | ✅ | terraform + ansible (deploy/terraform) |
| 8.10 | Information deletion | ✅ | Auto-purge по retention policy |
| 8.11 | Data masking | ✅ | PII-маскинг в audit_log |
| 8.12 | Data leakage prevention | ✅ | per-tenant фильтрация + audit |
| 8.13 | Backup | ✅ | YC daily backup |
| 8.15 | Logging | ✅ | audit_logs + Prometheus |
| 8.16 | Monitoring activities | ✅ | Grafana + Telegram alerts |
| 8.18 | Use of privileged utility programs | ⏳ | Регламент использования kubectl/psql |
| 8.20 | Networks security | ✅ | VPC изоляция (Yandex Cloud) |
| 8.21 | Security of network services | ✅ | TLS 1.3, no insecure ports exposed |
| 8.22 | Segregation of networks | ✅ | DB в private subnet, API в public subnet |
| 8.23 | Web filtering | ✅ | Caddy reverse proxy с rate-limiting |
| 8.24 | Use of cryptography | ✅ | TLS 1.3 + bcrypt + AES-256 |
| 8.25 | Secure development life cycle | ✅ | CI/CD + pre-commit hooks + code review |
| 8.26 | Application security requirements | ✅ | OWASP Top 10 для каждой фичи |
| 8.28 | Secure coding | ✅ | bandit + ruff + pre-commit |
| 8.29 | Security testing | ✅ | pytest + unit/integration tests |
| 8.30 | Outsourced development | ⏳ | NDA для подрядчиков |
| 8.31 | Separation of development and production | ✅ | Отдельные среды dev/staging/prod |
| 8.32 | Change management | ✅ | PR-review + CI gating |
| 8.33 | Test information | ✅ | Mock-данные, нет PII в тестах |
| 8.34 | Protection of audit info | ✅ | Audit-log append-only |

## Сводка

- **Реализовано (✅)**: 49 / 60 (82%)
- **В работе (⏳)**: 11 / 60 (18%)

**Готовность к ISO 27001:2022 сертификации**: технические контроли реализованы на 82%. Перед сертификацией необходимо завершить организационные меры (политики, регламенты, обучение).

**Сроки**:
- Q1 2026: завершение организационных контролей.
- Q2 2026: внутренний аудит.
- Q3 2026: внешний аудит и сертификация.
