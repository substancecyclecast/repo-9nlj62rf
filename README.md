# Mandate — Autonomous CFO Agent for Crypto-Native Orgs & DAOs

[![CI](https://github.com/substancecyclecast/repo-9nlj62rf/actions/workflows/ci.yml/badge.svg)](https://github.com/substancecyclecast/repo-9nlj62rf/actions) ![Python 3.12](https://img.shields.io/badge/python-3.12-blue) ![Tests](https://img.shields.io/badge/tests-66%20passing-brightgreen) ![Stellar](https://img.shields.io/badge/Stellar-testnet%20live-blueviolet)

> Connect your Safe / Squads multisig. Mandate sees incoming payments, converts to
> your chosen stablecoin, rebalances the treasury by policy, pays payroll and vendors
> in 90+ countries, keeps double-entry on-chain books, and prepares auditor-ready
> reports — driven by an LLM agent, not humans.

**Stripe Atlas + Rippling + Brex, for the on-chain world.**

> **Stellar Community Fund / CV Labs Accelerator candidate.** See [`docs/SCF_APPLICATION.md`](./docs/SCF_APPLICATION.md) for the full application.

This repository is a complete, runnable product (MMP), not a mockup. Every flow
below works end-to-end in **sandbox mode with no API keys or private keys**:

- Multi-chain treasury aggregation (EVM Safes + Solana Squads), NAV, allocation.
- An autonomous **CFO agent** that turns plain-English goals into audited tool calls.
- **Payroll**: import a contractor CSV → auto-route each payee to the cheapest chain
  or a fiat off-ramp → compliance screen → multisig proposals → execute.
- **Double-entry accounting** that stays balanced on every action.
- **Auditor-ready PDF** + **QuickBooks CSV** exports.
- **Usage-based billing** (bps take-rate + platform fee), MRR, and invoicing.
- **Production ops surface**: Prometheus `/metrics`, `/healthz` + `/readyz`
  probes, an immutable **audit trail**, **Slack/Telegram webhooks**, request-id
  tracing, and optional rate limiting.
- A polished **Next.js dashboard** (7 screens incl. Billing and Settings/Admin)
  over the whole thing.

See [`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md) for the full pitch, architecture,
business model, and go-to-market.

---

## Quick start

### Option A — Docker (one command)

```bash
docker compose up --build
```

- Dashboard → http://localhost:3000
- API docs → http://localhost:8000/docs

The backend seeds a realistic demo org ("Helios Labs DAO") on first boot.

### Option B — Local dev (no Docker)

**Backend** (Python 3.12):

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 22):

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

The frontend proxies `/api/*` to the backend (`MANDATE_API_BASE`, default
`http://localhost:8000`), so there is nothing else to configure.

---

## The 90-second demo

1. **Dashboard** — $4.25M NAV across 4 multisig wallets on 4 chains, with live
   policy recommendations (deploy idle cash, rebalance to target stablecoin %).
2. **CFO Agent** — type *"Deploy $250,000 idle USDC into the highest-yield venue"*;
   watch the agent call `list_yield_venues` → `deploy_yield` with a full audit trace.
3. **Payroll** — click **Run sample batch** (12 contractors, 10 countries). The agent
   routes each payee to the cheapest chain (Polygon/Solana) or a fiat rail
   (SEPA/SPEI), screens compliance, builds one multisig proposal per chain, and
   settles all of them — *"Paid 12 contractors in 0.02s."*
4. **Ledger & Reports** — books are still balanced; download the **Auditor PDF** and
   **QuickBooks CSV**.
5. **Billing & Revenue** — the same settled volume drives the take-rate invoice,
   estimated MRR, and the SWIFT savings delivered to the customer.
6. **Settings & Admin** — live `/readyz` status, the RBAC matrix, the immutable
   audit trail of every action, and the webhook delivery outbox (send a test event).

---

## Tests

```bash
cd backend && . .venv/bin/activate
PYTHONPATH=. pytest -q
```

66 tests cover the double-entry invariant, payroll parse→plan→propose→execute,
cheapest-chain routing, compliance screening, the agent core, Stellar/Soroban
policy + RWA, PDF generation, production auth/RBAC, and the ops layer (metrics
registry, audit log, webhook outbox, billing math, rate limiting).

Run `ruff check app tests` for lint. CI (`.github/workflows/ci.yml`) runs backend
lint+tests, frontend typecheck+build, and a Soroban contract build on every push.

---

## Repository layout

```
mandate/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── adapters/        Safe, Squads, Li.Fi, Bridge off-ramp, yield, compliance, pricing
│   │   ├── agent/           Tool registry + orchestrator (deterministic or LLM)
│   │   ├── api/             REST routes (treasury, agent, payments, ledger)
│   │   ├── core/            Config, DB, constants
│   │   ├── models/          SQLAlchemy models (org, treasury, ledger, payments, agent)
│   │   ├── reports/         Auditor PDF + QuickBooks CSV
│   │   └── services/        Ledger, treasury, routing, payroll, categorization, seed
│   ├── data/sample_payroll.csv
│   └── tests/
├── frontend/                Next.js 14 + Tailwind dashboard
├── docker-compose.yml
└── PROJECT_OVERVIEW.md
```

## Stellar ecosystem impact

Mandate brings **volume and users** to the Stellar network by routing cross-border
payroll through Stellar's rails:

| Feature | Detail |
|---------|--------|
| **Cross-border corridors** | 45+ EMEA/Africa countries via Stellar anchors (NIBSS, M-Pesa, SEPA Instant) |
| **Cost advantage** | ~67% cheaper than SWIFT ($0.00001/tx vs $25–50) |
| **Soroban policy engine** | On-chain spending limits, allowlists, 24h time-locked withdrawals |
| **Path payments** | Atomic USDC→EURC/NGNC swaps on Stellar DEX |
| **RWA/T-Bills** | Tokenized US T-Bills (5.25% APY) and EU bonds on Stellar |
| **Volume at scale** | 500 orgs × monthly payroll = **100K+ tx/month** on Stellar |

See [`docs/SCF_APPLICATION.md`](./docs/SCF_APPLICATION.md) for the full Stellar
Community Fund application with impact metrics and budget breakdown.

## Sandbox vs. live

Everything defaults to **sandbox**: deterministic prices, multisig proposal building
without private keys, and simulated execution — so the product is fully demonstrable
offline. Set `MANDATE_INTEGRATION_MODE=live` and supply keys to wire the same
adapters to real services (Safe Transaction Service, Squads, Li.Fi, Bridge.xyz,
**Stellar Horizon + Soroban RPC**).
The agent can be upgraded from the deterministic planner to Claude/GPT by setting
`MANDATE_LLM_PROVIDER` and the matching API key.

### Stellar testnet mode

```bash
export MANDATE_INTEGRATION_MODE=live
export MANDATE_STELLAR_NETWORK=testnet
export MANDATE_STELLAR_SIGNING_KEY=S...  # testnet secret key
```

Run `python scripts/stellar_testnet_bootstrap.py` to fund accounts, set up
trustlines, and create test asset liquidity. Then run a payroll batch to see
**real transactions** in [Stellar Expert](https://stellar.expert/explorer/testnet).
