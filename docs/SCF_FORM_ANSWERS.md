# SCF Build Interest Form — Ready-to-Paste Answers

---

## Project Title

Mandate — Autonomous CFO Agent for Crypto-Native Organizations

---

## Project Description (max 1100 chars)

Mandate is an AI-powered CFO agent that manages treasury, payroll, and accounting for DAOs on Stellar.

Problem: 15,000+ crypto orgs manage $200B+ in treasuries via spreadsheets, pay contractors manually across 40+ countries, and waste $25-50 per SWIFT transfer.

Solution: Upload a contractor CSV — in 90s the AI agent routes payments to the cheapest rail (prioritizing Stellar for EMEA/Africa), screens compliance, settles via multisig, and produces auditor-ready books.

Key capabilities:
- Multi-chain treasury aggregation (EVM, Solana, Stellar)
- AI CFO Agent with 13 tools and full audit trail
- Cross-border payroll via Stellar anchors (45+ countries, 67% cheaper than SWIFT)
- Soroban policy engine: spending limits, allowlists, 24h timelocks
- Path payments: atomic USDC-EURC/NGNC swaps on Stellar DEX
- RWA/T-Bills on Stellar (5.25% APY, MiCA-compliant)
- Double-entry accounting with PDF + QuickBooks export

Fully built product — 66 tests passing, CI green, real Stellar testnet transactions verified.

---

## Project Category

End-User Application

---

## Current Traction (max 1000 chars)

- Full working product: FastAPI backend + Next.js 14 frontend + Soroban smart contract
- 66 automated tests passing (25 Stellar-specific), CI green
- Real Stellar testnet transactions verified (payments, path payments, Soroban policy)
- Live demo: 15 contractors paid across 4 networks in 0.05s
- 7-screen dashboard: Treasury, CFO Agent, Payroll, Stellar & RWA, Ledger, Billing, Settings
- Deployed: https://mandatecfo.vercel.app
- Full CI pipeline (backend lint+tests, frontend typecheck+build, Soroban build)
- Testnet bootstrap: automated account creation, Friendbot funding, trustlines, DEX liquidity

Evidence:
- Stellar tx: https://stellar.expert/explorer/testnet/tx/63e8beb605fb673ccd5ad24f06225436916d4b445f851662ca3d5ea0a00e399b
- GitHub: https://github.com/substancecyclecast/repo-9nlj62rf

---

## Website

https://mandatecfo.vercel.app

---

## Planned Stellar Integration (max 1100 chars)

Mandate integrates deeply with Stellar at multiple levels:

1. Stellar SDK (Python): Real XDR transactions — payments, path payments (strict send/receive), account management via Horizon API.

2. Soroban Smart Contracts: Rust policy engine on testnet enforcing per-tx limits ($25K), daily caps ($100K), allowlists, and 24h time-locked withdrawals. Functions: check_transfer(), queue_transfer(), execute_pending(), cancel_pending().

3. SEP-31 Anchors: Fiat off-ramps via Cowrie (Nigeria), M-Pesa (Kenya), SEPA Instant (EU), Faster Payments (UK), GhIPSS (Ghana). 45+ countries.

4. Path Payments: Atomic USDC to EURC/NGNC swaps on Stellar DEX for cross-currency settlement.

5. Testnet: Automated bootstrap (Friendbot, trustlines, test assets, DEX liquidity). Ready for mainnet.

6. Volume: Each 15-contractor payroll batch = 15+ Stellar txs. At 500 orgs = 100K+ txs/month.

Status: Testnet live with verified transactions. Mainnet deployment as first milestone.

---

## Build Track

Integration Track

(Mandate integrates with existing Stellar ecosystem: SDK, Soroban, SEP-31 anchors, path payments, DEX)

---

## Submitter type

Individual

---

## Email

scaleblinkk@vk.com

---

## Team Description

Solo founder with full-stack expertise building toward a core team.

Current (1 person):
- Founder & CEO — Full-stack developer experienced in fintech, blockchain, and AI/ML. Built entire Mandate product solo: FastAPI backend, Next.js frontend, Soroban contract (Rust), Stellar SDK integration, LLM agent orchestration, double-entry accounting engine.

Hiring plan (with SCF funding):
- CTO: Stellar/Rust experience (Soroban, stellar-sdk)
- Head of BD: DAO/crypto treasury network

Stack: Python (FastAPI, SQLAlchemy), TypeScript (Next.js, React), Rust (soroban-sdk), Stellar SDK, LLM integration (Anthropic/OpenAI function calling), Docker, CI/CD.

---

## Referral Information

No
