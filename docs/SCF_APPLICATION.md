# Stellar Community Fund (SCF) Application — Mandate

---

## Project Name

**Mandate — Autonomous CFO Agent for Crypto-Native Organizations**

---

## Project Description (Short)

Mandate is an AI-powered autonomous CFO agent that manages treasury, payroll, and accounting for DAOs and crypto-native organizations. It routes cross-border payments through Stellar's rails (45+ EMEA/Africa countries, 67% cheaper than SWIFT), enforces spending policies via Soroban smart contracts, and produces auditor-ready financial reports — all driven by an LLM agent, not humans.

---

## Impact on the Stellar Ecosystem

### Transaction Volume

Every payroll batch of 15 contractors generates 15+ on-chain Stellar transactions. At target scale (500 organizations × monthly payroll), Mandate will drive **100,000+ transactions per month** on the Stellar network.

### New Users

Mandate brings **DAO treasurers** — a segment that currently uses EVM-only tools (Safe, Utopia, Request Finance) — onto Stellar for the first time. These are high-value users managing $1M–$100M+ treasuries.

### Stellar-Native Features Used

| Feature | How Mandate Uses It |
|---------|-------------------|
| **Path Payments** | Atomic USDC→EURC/NGNC swaps on Stellar DEX for cross-currency settlement |
| **SEP-31 Anchors** | Cross-border fiat off-ramps via Stellar anchors (NIBSS, M-Pesa, SEPA Instant) |
| **Soroban Smart Contracts** | On-chain policy enforcement: spending limits, allowlists, 24h time-locked withdrawals |
| **Multi-asset Support** | USDC, EURC (MiCA-compliant), NGNC, and tokenized T-Bills on Stellar |
| **Low-cost Transactions** | $0.00001/tx enables micro-payment use cases (contractor payroll, grants) |

### EMEA/Africa Focus

Mandate specifically targets the Stellar-dominant corridors:

- **45+ countries** with Stellar anchor coverage
- **Nigeria** (NIBSS/NIP via Cowrie, NGNC stablecoin)
- **Kenya/East Africa** (M-Pesa via Stellar anchors)
- **EU** (SEPA Instant, EURC under MiCA)
- **UK** (Faster Payments)
- **Ghana** (GhIPSS)
- **South Africa** (local bank settlement)

**Cost advantage:** ~67% cheaper than SWIFT for the same corridors.

---

## Technical Architecture

```
Frontend (Next.js 14)
    ↓
FastAPI Backend (Python 3.12)
    ↓
Agent Orchestrator (LLM tool-use loop: Anthropic / OpenAI)
    ↓
13 Tools (treasury, payroll, yield, Stellar, RWA, compliance)
    ↓
Adapters (Safe, Squads, Stellar, Soroban, Anchors, DeFi)
    ↓
Double-Entry Ledger (always balanced, auditable)
```

### Stellar Integration Stack

- **stellar-sdk** (Python) — TransactionBuilder, Payment ops, Path Payment ops
- **SorobanServer** — contract invocation via `simulate_transaction()`
- **Horizon API** — account loading, transaction submission, ledger queries
- **Friendbot** — testnet account funding
- **Stellar Expert** — transaction verification links

### Soroban Contract (`contracts/soroban-policy/`)

Written in Rust using `soroban-sdk`. Enforces:

1. **Per-transaction spending limit** (configurable, default $25,000)
2. **Daily aggregate cap** (default $100,000)
3. **Compliance allowlist** (only pre-approved addresses)
4. **Time-locked withdrawals** — transfers above threshold queued for 24h
   - `queue_transfer()` → creates pending with `unlock_at` timestamp
   - `execute_pending()` → executes after timelock elapsed
   - `cancel_pending()` → admin-only cancellation

Contract has 5 Rust tests covering timelock scenarios, allowlist enforcement, and spending limits.

### Key Repositories / Files

| File | Purpose |
|------|---------|
| `backend/app/adapters/chains.py` | StellarAdapter — builds and submits real XDR transactions |
| `backend/app/adapters/soroban_policy.py` | Soroban contract invocation (check_transfer, queue_timelock) |
| `backend/app/adapters/stellar_anchor.py` | SEP-31 anchor integration (45+ countries) |
| `contracts/soroban-policy/src/lib.rs` | Soroban policy contract (Rust) |
| `scripts/stellar_testnet_bootstrap.py` | Testnet setup script (Friendbot + assets + DEX) |
| `backend/app/agent/llm.py` | Multi-step LLM agentic loop |

---

## What We've Built (Working Product)

Mandate is a **complete, runnable product** (MMP) — not a mockup or prototype.

### Core Features (all working)

- **Multi-chain treasury aggregation** — EVM (Safe), Solana (Squads), Stellar
- **AI CFO Agent** — 13 tools, deterministic + LLM planner, full audit trail
- **Global payroll** — upload CSV → auto-route to cheapest chain/fiat rail → settle
- **Stellar cross-border** — SEP-31 anchors, path payments, $0.00001/tx
- **Soroban policy engine** — on-chain spending limits, allowlists, timelocks
- **Double-entry accounting** — always balanced, auditor-ready PDF + QuickBooks CSV
- **RWA/T-Bills** — tokenized US T-Bills (5.25% APY) on Stellar
- **Production ops** — Prometheus metrics, health probes, audit trail, webhooks
- **Dashboard** — Next.js 14 with 7 screens

### Test Coverage

- **66 unit tests** passing (including 25 Stellar-specific)
- **3 on-chain integration tests** (real Stellar testnet transactions)
- CI pipeline: backend lint+tests, frontend typecheck+build, Soroban contract build
- All CI checks passing

### Demo

```bash
docker compose up --build
# Dashboard → http://localhost:3000
# API docs → http://localhost:8000/docs
```

90-second demo flow: Dashboard → Stellar page → Agent run → Payroll sample → Ledger → PDF export.

---

## Team

**[Your Name]** — Founder & CEO
- [Your background — fill in]
- [Relevant experience — fill in]

**Looking for:**
- CTO with Stellar/Rust experience (Soroban, stellar-sdk)
- Head of BD with DAO/crypto treasury network

---

## Budget & Use of Funds

### Requesting: $100,000

| Category | Amount | Purpose |
|----------|--------|---------|
| **Engineering** | $40,000 (40%) | Stellar mainnet deployment, co-signer module, mobile app |
| **BD & Sales** | $30,000 (30%) | Pilot customer acquisition, anchor partnerships (Cowrie, Flutterwave, YellowCard) |
| **Compliance & Legal** | $20,000 (20%) | MiCA registration prep, SOC 2 readiness |
| **Operations** | $10,000 (10%) | Infrastructure (hosting, monitoring), testnet operations |

### Milestones

| Milestone | Timeline | Deliverable |
|-----------|----------|-------------|
| **M1: Mainnet deployment** | Month 1-2 | Mandate live on Stellar mainnet with real transactions |
| **M2: First pilot customers** | Month 2-3 | 5 DAOs onboarded, processing real payroll through Stellar |
| **M3: Anchor integrations** | Month 3-4 | Live fiat off-ramps via Cowrie (Nigeria), Flutterwave (Africa) |
| **M4: Scale** | Month 4-6 | 20+ paying customers, $100K+ monthly GPV through Stellar |

### Expected ROI for Stellar

At 20 customers processing $5M/month GPV through Stellar:
- **~15,000 transactions/month** on Stellar network
- **~$100K/month** in volume flowing through Stellar DEX (path payments)
- **~200 new Stellar accounts** (contractor wallets)
- **Proof of concept** for Stellar as B2B cross-border infrastructure

---

## Competitive Advantage

### Why Mandate is unique on Stellar

1. **Only solution** combining AI agent + Stellar + multi-chain + accounting
2. **67% cheaper** cross-border via Stellar (vs SWIFT/SEPA)
3. **On-chain policy** via Soroban smart contracts (no competitor has this)
4. **Working product** — fully demonstrable, not slides
5. **Defensible** — ledger + payee graph + audit trail = switching costs

### Competitors (none use Stellar)

| | Mandate | Safe/Den | Utopia | Request | Deel |
|--|---------|----------|--------|---------|------|
| AI Agent | ✅ | ❌ | ❌ | ❌ | ❌ |
| Stellar | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cross-border (45+) | ✅ | ❌ | ❌ | ❌ | ✅ (expensive) |
| On-chain policy | ✅ Soroban | ❌ | ❌ | ❌ | ❌ |
| Double-entry | ✅ | ❌ | ❌ | Partial | ✅ |

---

## Market Opportunity

- **TAM:** $50B+ (crypto treasury management + adjacent fintech)
- **SAM:** $5B (crypto-native orgs with $1M+ treasuries)
- **SOM:** $500M (DAOs and crypto companies in Stellar-dominant corridors)
- **15,000+** crypto orgs with $1M+ treasuries
- **$200B+** in multisig wallets (Safe alone: $100B+)

### Why now

- **MiCA + GENIUS Act** legitimize stablecoin payments (regulatory tailwind)
- **Frontier AI models** enable reliable tool-use (Claude 3.5, GPT-4o)
- **Soroban launch** enables sophisticated on-chain policy enforcement
- **Pain is acute:** every DAO treasurer feels payroll pain monthly

---

## Stellar-Specific Value Proposition

### For the Stellar Development Foundation

1. **Volume:** 100K+ tx/month at scale, all on Stellar
2. **Use case:** B2B treasury management — a new vertical for Stellar
3. **EMEA/Africa:** Mandate targets exactly the corridors where Stellar excels
4. **Soroban showcase:** real-world enterprise use of Soroban smart contracts
5. **Developer ecosystem:** open-source Stellar integration patterns

### For Stellar Anchor Partners

1. **Distribution:** Mandate becomes a channel for anchor volume
2. **Automation:** no manual anchor interactions — everything programmatic via SEP-31
3. **Scale:** each customer brings 10-200 recurring payees

### For Stellar Users

1. **Lower cost:** 67% cheaper than SWIFT for the same corridors
2. **Faster:** 5-second settlement vs 2-5 day SWIFT
3. **Compliant:** KYC/AML screening built into every transaction
4. **Auditable:** double-entry books + on-chain audit trail

---

## Links

- **GitHub:** [Repository URL]
- **Demo:** `docker compose up` (sandbox mode, no keys needed)
- **Testnet:** Run `scripts/stellar_testnet_bootstrap.py` to see real Stellar transactions
- **Documentation:** `PROJECT_OVERVIEW.md`, `docs/PITCH_DECK.md`

---

## Contact

- **Email:** [your email]
- **Twitter:** [your handle]
- **Telegram:** [your handle]
