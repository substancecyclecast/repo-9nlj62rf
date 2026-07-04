# Security & Compliance Overview

This document summarizes Mandate's security posture for diligence by acquirers,
auditors, and accelerator reviewers. Mandate is a treasury-operations layer; it
**never takes custody of funds** — it builds and co-signs multisig proposals
bounded by policy.

## Custody & key management
- **No custody.** Mandate connects to a customer's existing Safe (EVM), Squads
  (Solana), or Stellar multisig. The agent proposes transactions; the customer's
  own signers (or a policy-bounded co-signer module) approve them.
- **Bounded autonomy.** Autonomous transfers are capped (`MAX_AGENT_AUTONOMOUS_
  TRANSFER_USD`, default $25k). Above the cap, human signatures are required.
- **On-chain policy.** A Soroban smart contract enforces hard limits independent
  of the application: per-tx cap ($25k), daily cap ($100k), recipient allowlist,
  and a 24h timelock for withdrawals over $100k. This converts "trust the AI"
  into "trust the math."

## Authentication & authorization
- JWT (HS256) / Privy auth, gated by `MANDATE_AUTH_ENABLED`.
- Role-based access control with five roles (Owner, Admin, Member, Viewer,
  Agent) and a least-privilege permission matrix (`app/core/auth.py`).
- Tenant isolation: every resource is scoped to an `organization_id`.

## Auditability
- **Immutable audit log** of every significant action (actor, action, resource,
  request id, JSON detail), queryable per org and shown in the admin UI.
- **Full agent trace.** Every autonomous run stores its goal and each tool call
  with arguments and observations.
- **Double-entry ledger** that stays balanced on every action, with auditor-ready
  PDF and QuickBooks CSV exports.

## Operational security
- Request-id propagation on every response for traceability.
- Optional per-IP rate limiting; DDoS-sensitive endpoints return `429` with
  `Retry-After`.
- `/healthz` + `/readyz` probes and Prometheus `/metrics` for monitoring/alerting.
- Database backups via `scripts/backup_db.sh` (online SQLite snapshot or
  `pg_dump`), with retention; schedulable by cron.
- Secrets are read from the environment only; none are committed. `.env` is
  git-ignored and a redacted `.env.example` is provided.

## Compliance
- Counterparty screening (sanctions/restricted jurisdictions) on every payee
  before a payment is proposed; blocked payees are surfaced, not silently
  dropped.
- Stablecoin selection is jurisdiction-aware (e.g. EURC for EU/MiCA contexts).
- Off-ramp partners (Bridge, Cowrie, Flutterwave, YellowCard) are KYB/KYC-gated
  in live mode.

## Reporting a vulnerability
Email security@mandate.finance (placeholder) with details and reproduction steps.
Please do not open public issues for security reports.
