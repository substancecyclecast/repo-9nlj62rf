# Mandate — Acquisition / Asset-Sale Memo

> A turnkey, production-ready **Autonomous CFO** product for crypto-native orgs and
> DAOs. This memo is written for a buyer evaluating Mandate as an acqui-product /
> IP-and-codebase acquisition.

---

## 1. What you are buying

A complete, runnable software product (not a mockup) plus its documentation and
go-to-market assets:

- **Backend** — FastAPI service: multi-chain treasury, autonomous agent with a
  bounded tool registry, global payroll with cheapest-chain routing, double-entry
  ledger, auditor PDF + QuickBooks exports, production auth/RBAC, live adapter
  switching, **billing**, **audit log**, **webhooks**, **metrics**, and
  **health/readiness** probes.
- **Frontend** — Next.js 14 + Tailwind dashboard, **7 screens** (Dashboard, CFO
  Agent, Payroll, Stellar & RWA, Ledger & Reports, Billing & Revenue, Settings &
  Admin).
- **Smart contract** — Soroban policy contract (Rust) enforcing per-tx/daily caps,
  allowlists, and timelocks on-chain.
- **Quality bar** — **66 automated tests passing**, `ruff`-clean backend, a
  type-checked frontend that builds, and a **CI pipeline** that gates all three.
- **Docs** — pitch deck, financial model, GTM, competitive analysis, one-pager,
  deployment guide, security overview, accelerator applications, and DAO outreach.

Everything runs **offline in sandbox mode** with zero API keys, so a buyer can
evaluate the full product in one command (`docker compose up`).

## 2. Why it's valuable

- **Real, defensible scope.** This is the finance back-office (payroll + treasury
  + books + compliance) for on-chain orgs — "Stripe Atlas + Rippling + Brex,
  driven by an LLM." Existing crypto tools are wallets, not finance teams.
- **A wedge nobody owns.** EMEA/Africa cross-border payroll over Stellar at
  ~$0.00001/tx and 5s finality, ~67% cheaper than SWIFT. Big fintechs (Deel,
  Rippling) charge 3–5% for emerging-market payouts.
- **Trust-by-math.** On-chain Soroban policy limits make autonomous payments
  palatable to treasurers — the #1 objection ("I can't let an AI move money") is
  answered structurally, not with a promise.
- **Built to be operated.** Metrics, readiness probes, audit trail, webhooks,
  rate limiting, backups, and CI mean a buyer can deploy and run it on day one,
  not re-platform it.

## 3. Monetization (already implemented in-product)

The Billing screen and `billing_service` implement the revenue model:

- **Take-rate**: 25 bps (configurable) on settled payment volume.
- **Platform fee**: flat monthly SaaS fee per org (default $2,000).
- The product computes current invoice, estimated MRR, lifetime take-rate
  revenue, and the SWIFT savings delivered to the customer — all from live data.

Illustrative unit economics (configurable, not a forecast): an org settling
$1.5M/mo of payroll generates **$3,750/mo take-rate + $2,000 platform fee =
$5,750/mo** at the default rates.

## 4. Technical due-diligence checklist

| Item | Status |
|---|---|
| Runs in one command (Docker) | ✅ |
| Runs offline / no secrets needed for demo | ✅ |
| Automated tests | ✅ 66 passing |
| Lint (ruff) clean | ✅ |
| Frontend typechecks + builds | ✅ |
| CI pipeline | ✅ (`.github/workflows/ci.yml`) |
| Auth + RBAC + tenant isolation | ✅ |
| Audit trail of all actions | ✅ |
| Monitoring (metrics + health/readiness) | ✅ |
| DB backups | ✅ (`scripts/backup_db.sh`) |
| On-chain policy contract | ✅ (Soroban, Rust) |
| Live integration paths (Safe, Stellar, off-ramps) | ✅ (adapter switch) |
| API docs (OpenAPI + Postman) | ✅ (`docs/api/`) |

## 5. What a buyer must add to go live

These are explicitly *not* hidden — they are the normal "turn it on" steps:

1. Provider API keys (Bridge, Flutterwave, Cowrie, YellowCard, Chainalysis) and
   KYB approval where required.
2. Deploy and initialize the Soroban contract (script provided in `MANDATE_PLAN`).
3. Configure a Safe co-signer module for autonomous signing within limits.
4. Set `MANDATE_INTEGRATION_MODE=live`, point `MANDATE_DATABASE_URL` at Postgres,
   set `MANDATE_AUTH_ENABLED=true`, and wire Slack/Telegram for alerts.

## 6. Assets included in the sale

- Full source (backend, frontend, contract) under one repo.
- All documentation in `docs/` and the root markdown files.
- The seeded demo organization ("Helios Labs DAO") for instant evaluation.
- Accelerator application drafts and DAO outreach templates.

---

*Prepared as part of the product package. Figures for take-rate/fees are product
defaults and configuration examples, not audited financials.*
