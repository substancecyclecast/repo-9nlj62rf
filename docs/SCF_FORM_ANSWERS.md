# SCF Build Interest Form — Ready-to-Paste Answers

---

## Project Title

Mandate — Autonomous CFO Agent for Crypto-Native Organizations

---

## Project Description

Mandate is an AI-powered autonomous CFO agent that manages treasury, payroll, and accounting for DAOs and crypto-native organizations on Stellar.

The problem: 15,000+ crypto organizations manage $200B+ in treasuries using spreadsheets, pay contractors manually across 40+ countries, have no real accounting, and waste $25-50 per SWIFT transfer.

Mandate solves this: Upload a contractor CSV → in 90 seconds the AI agent routes every payment to the cheapest rail (prioritizing Stellar for EMEA/Africa corridors), screens compliance, settles via multisig, and produces auditor-ready books — all autonomously.

Key capabilities:
- Multi-chain treasury aggregation (EVM Safe, Solana Squads, Stellar wallets)
- AI CFO Agent with 13 tools, full audit trail, LLM-powered decision making
- Cross-border payroll through Stellar anchors (45+ EMEA/Africa countries, 67% cheaper than SWIFT)
- Soroban smart contract policy engine: on-chain spending limits, allowlists, 24h time-locked withdrawals
- Path payments: atomic USDC→EURC/NGNC swaps on Stellar DEX
- RWA/T-Bills: tokenized US T-Bills (5.25% APY) on Stellar, MiCA-compliant
- Double-entry accounting: always balanced, auditor-ready PDF + QuickBooks CSV export
- Usage-based billing: take-rate on GPV + SaaS seats + FX spread + yield share

The product is fully built and runnable — not a prototype or slides. 66 tests passing, CI green, real Stellar testnet transactions verified.

---

## Project Category

End-User Application

---

## Current Traction

- Full working product (MMP): FastAPI backend + Next.js 14 frontend + Soroban smart contract
- 66 automated tests passing (25 Stellar-specific), CI pipeline green
- Real Stellar testnet transactions verified (payment + path payment + Soroban policy check)
- Live demo: 15 contractors paid across 4 networks in 0.05 seconds
- 7-screen dashboard: Treasury, CFO Agent, Payroll, Stellar & RWA, Ledger, Billing, Settings
- Deployed on Vercel: https://frontend-livid-eta-jp0rtaykhc.vercel.app
- GitHub repository with full CI (backend lint+tests, frontend typecheck+build, Soroban build)
- Testnet bootstrap script that creates accounts, funds via Friendbot, sets up trustlines, creates DEX liquidity, and submits a real payment — all automated

Evidence:
- Stellar Explorer tx: https://stellar.expert/explorer/testnet/tx/63e8beb605fb673ccd5ad24f06225436916d4b445f851662ca3d5ea0a00e399b
- GitHub: https://github.com/substancecyclecast/repo-9nlj62rf

---

## Website

https://frontend-livid-eta-jp0rtaykhc.vercel.app

---

## Planned Stellar Integration

Mandate deeply integrates with the Stellar tech stack at multiple levels:

1. Stellar SDK (Python): We use stellar-sdk to build and submit real XDR transactions — payments, path payments (strict send/receive), and account management operations via Horizon API.

2. Soroban Smart Contracts: Our policy engine is a Rust smart contract (soroban-sdk) deployed on Stellar testnet. It enforces per-transaction spending limits ($25K default), daily aggregate caps ($100K), compliance allowlists, and 24-hour time-locked withdrawals. Functions: check_transfer(), queue_transfer(), execute_pending(), cancel_pending().

3. SEP-31 Anchors: Cross-border fiat off-ramps via Stellar anchor network — Cowrie (Nigeria/NIBSS), M-Pesa (Kenya/East Africa), SEPA Instant (EU), Faster Payments (UK), GhIPSS (Ghana). 45+ countries covered.

4. Path Payments: Atomic USDC→EURC and USDC→NGNC swaps on the Stellar DEX for cross-currency settlement without intermediaries.

5. Stellar Testnet: Full testnet integration with automated bootstrap script (Friendbot funding, trustline setup, test asset issuance, DEX liquidity creation). Ready for mainnet migration.

6. Volume Impact: Each payroll batch of 15 contractors generates 15+ Stellar transactions. At target scale (500 organizations), this drives 100,000+ transactions/month on Stellar.

Current status: Testnet live with verified transactions. Mainnet deployment planned as first milestone.

---

## Build Track

Seed

---

## Submitter type

Company/Startup

---

## Email

scaleblinkk@vk.com

---

## Team Description

Solo founder with full-stack development expertise, building toward a core team:

Current team (1 person):
- Founder & CEO — Full-stack developer with experience in fintech, blockchain integration, and AI/ML. Built the entire Mandate product solo: FastAPI backend, Next.js frontend, Soroban smart contract (Rust), Stellar SDK integration, LLM agent orchestration, and double-entry accounting engine.

Looking to hire (with SCF funding):
- CTO with Stellar/Rust experience (Soroban smart contracts, stellar-sdk)
- Head of BD with DAO/crypto treasury network

Technical stack expertise: Python (FastAPI, SQLAlchemy), TypeScript (Next.js, React), Rust (Soroban/soroban-sdk), Stellar SDK, LLM integration (Anthropic/OpenAI function calling), Docker, CI/CD.

---

## Referral Information

No

---

## Notes for Manual Entry

The user needs to:
1. Log into https://communityfund.stellar.org/dashboard
2. Find the SCF Build Interest Form
3. Copy-paste each answer above into the corresponding field
4. Review and submit
