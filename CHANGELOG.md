# Changelog

All notable changes to Mandate are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [1.1.0] — Production hardening & monetization

Adds the operational and revenue surface expected of an acquirable fintech SaaS,
on top of the existing autonomous-CFO product. No breaking API changes.

### Added
- **Observability**
  - Prometheus exposition at `GET /metrics` (request counters/latency histograms,
    emitted-event counters, rate-limit counters, uptime).
  - `GET /healthz` (liveness) and `GET /readyz` (readiness — verifies the DB and
    reports environment + integration mode).
  - `RequestContextMiddleware`: per-request `X-Request-ID` and `X-Response-Time-ms`
    headers, plus automatic metrics for every route (path templated to keep
    cardinality low).
- **Immutable audit trail** (`audit_logs`) recording every significant action
  (agent runs, payroll execution) with actor, resource, and JSON detail; exposed
  at `GET /api/v1/orgs/{id}/audit` and surfaced in the new Settings screen.
- **Event notifications** (`webhook_deliveries` outbox) for Slack and Telegram,
  emitted on payroll execution and agent runs. Durable in sandbox (status
  `skipped`), live when `MANDATE_SLACK_WEBHOOK_URL` / Telegram creds are set.
  Test endpoint: `POST /api/v1/orgs/{id}/webhooks/test`.
- **Usage-based billing** (`billing_service`): bps take-rate on settled volume +
  flat platform fee → current invoice, estimated MRR, lifetime revenue, and SWIFT
  savings. Endpoints `GET …/billing/summary` and `GET …/billing/invoice`.
- **Rate limiting** middleware (sliding window per IP, opt-in via
  `MANDATE_RATE_LIMIT_ENABLED`), with health/metrics/docs exempt.
- **Frontend**: new **Billing & Revenue** and **Settings & Admin** screens; both
  wired to live backend data. `StatCard` gains a `blue` accent.
- **Ops tooling**: `scripts/backup_db.sh` (SQLite online backup / `pg_dump` for
  Postgres, with retention) and `scripts/export_openapi.py` (writes
  `docs/api/openapi.json` + a Postman collection).
- **CI**: `.github/workflows/ci.yml` runs backend ruff+pytest, frontend
  typecheck+build, and a Soroban contract build.

### Changed
- `config.Settings` extended with rate-limit, webhook, and billing settings.
- README/PROJECT_OVERVIEW updated to reflect the 7-screen dashboard and ops layer.

### Fixed
- Cleared all pre-existing `ruff` findings (unused imports/vars) so the repo lints
  clean, and resolved TypeScript errors in the Stellar screen so `next build`
  passes with strict type checking.

### Tests
- Test suite grows from 59 to **66** passing (new `tests/test_ops.py` covers the
  metrics registry, audit log, webhook outbox, billing math, and rate limiting).

## [1.0.0] — Initial product
- Multi-chain treasury, autonomous CFO agent, global payroll with cheapest-chain
  routing, double-entry ledger, auditor PDF + QuickBooks CSV, Stellar/Soroban
  policy + RWA, production auth/RBAC, and live adapter switching.
