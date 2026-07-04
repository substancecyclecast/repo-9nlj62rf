# Stellar / CV Labs Accelerator — Evaluation Rubric

How Mandate maps to accelerator evaluation criteria.

---

## 1. Stellar Ecosystem Value

| Criterion | Mandate's answer | Evidence |
|-----------|-----------------|----------|
| Does the project bring users/volume to Stellar? | Every payroll batch generates 15+ on-chain transactions; 500 orgs × monthly payroll = 100K+ tx/month | `backend/app/services/payroll_service.py` — cheapest-chain routing sends EMEA/Africa through Stellar |
| Does it use Stellar-native features? | Path payments (USDC→EURC/NGNC), SEP-31 anchors, Soroban smart contracts for policy enforcement | `backend/app/adapters/chains.py` — `StellarAdapter.build_path_payment()` |
| Does it use Soroban? | On-chain spending limits, allowlists, and time-locked withdrawals via deployed Soroban contract | `contracts/soroban-policy/src/lib.rs` — `queue_transfer()`, `execute_pending()`, `cancel_pending()` |

## 2. Product Readiness

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Working product (not just slides) | ✅ Full stack running | `backend/` (FastAPI), `frontend/` (Next.js 14), `contracts/` (Soroban) |
| Test coverage | ✅ 66 tests passing | `pytest -q` → 66 passed |
| Live testnet transactions | ✅ Real Stellar testnet | `scripts/stellar_testnet_bootstrap.py`, `tests/test_onchain.py` |
| Demo-able in < 90 seconds | ✅ Upload CSV → pay 15 contractors → PDF report | `backend/data/sample_payroll.csv` |

## 3. Market & Traction

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Clear target market | ✅ DAOs and crypto-native treasuries ($50B+ TAM) | `docs/GO_TO_MARKET.md` |
| Competitive differentiation | ✅ Only AI agent + Stellar + multi-chain + accounting | `PROJECT_OVERVIEW.md` § 5 |
| GTM plan | ✅ Accelerator → Safe App Store → Enterprise | `docs/GO_TO_MARKET.md` |
| Revenue model | ✅ SaaS + take rate + FX spread + yield share | `docs/ONE_PAGER.md` |

## 4. Technical Architecture

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Clean architecture | ✅ Adapter pattern, service layer, tool registry | `backend/app/adapters/`, `backend/app/services/` |
| Security | ✅ RBAC, JWT auth, on-chain policy enforcement | `backend/app/core/auth.py`, Soroban contract |
| Multi-chain | ✅ EVM (Safe), Solana (Squads), Stellar | `backend/app/adapters/chains.py` |
| API design | ✅ REST API with OpenAPI docs | `backend/app/api/` |

## 5. EMEA/Africa Focus

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Cross-border corridors | ✅ 45+ countries | `backend/app/adapters/stellar_anchor.py` |
| Local payment rails | ✅ NIBSS/NIP, M-Pesa, GhIPSS, SEPA, FPS | Anchor fee tables in `stellar_anchor.py` |
| Local stablecoins | ✅ EURC (EU/MiCA), NGNC (Nigeria) | Path payment support |
| Cost advantage over SWIFT | ✅ ~67% cheaper | Cross-border calculator in `routing_service.py` |

## 6. Team & Execution

| What we need from the accelerator |
|-----------------------------------|
| Mentorship — treasury management domain expertise |
| Network — intros to 50+ DAOs for pilots |
| Brand — SDF/CV Labs endorsement for enterprise credibility |
| Funding — pre-seed to hire CTO (Stellar/Rust) + BD |

---

## Quick reference: key files for evaluators

```
scripts/stellar_testnet_bootstrap.py   — Run this first to see real Stellar transactions
tests/test_onchain.py                  — On-chain integration tests (real testnet tx)
backend/app/adapters/chains.py         — StellarAdapter with live transaction support
contracts/soroban-policy/src/lib.rs    — Soroban policy contract with timelock
backend/app/agent/llm.py               — Multi-step LLM tool-use loop
backend/app/services/payroll_service.py — Cross-border payroll routing
```
