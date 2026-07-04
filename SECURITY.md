# Security Policy

## Reporting Vulnerabilities

Email security issues to **security@mandate.finance**. Do NOT open a public
GitHub issue. We will acknowledge within 48 hours and aim to patch critical
issues within 7 days.

## Architecture Security

### Key Management

- The Mandate agent **never holds private keys** in the application layer.
- EVM: transactions are built as Safe multisig proposals — owners co-sign
  externally.
- Solana: transactions are built as Squads proposals.
- Stellar: transactions are built and signed with `MANDATE_STELLAR_SIGNING_KEY`,
  which should be a **testnet key** for development. On mainnet, use a regulated
  custody provider (e.g. Fireblocks, Anchorage) via SEP-0030.

### On-Chain Policy Enforcement (Soroban)

The Soroban smart contract (`contracts/soroban-policy/`) enforces:

1. **Per-transaction spending limit** — rejects any single transfer above the
   configured cap (default: $25,000).
2. **Daily aggregate cap** — rejects transfers that would push the day's total
   above the limit (default: $100,000).
3. **Compliance allowlist** — only pre-approved addresses can receive funds.
4. **Time-locked withdrawals** — transfers above the timelock threshold
   (default: $100,000) must be queued for 24 hours before execution. Admin can
   cancel pending transfers.

These checks are enforced at the smart contract level and cannot be bypassed by
the application.

### Authentication & Authorization

- RBAC with five roles: Owner, Admin, Member, Viewer, Agent.
- JWT (HS256) or Privy for auth. Disabled by default in sandbox/dev.
- Tenant isolation: every query is scoped to `org_id`.

### Soroban Contract Audit Checklist

| Item | Status |
|------|--------|
| Integer overflow in spending limits | Safe — Soroban's `i128` handles all amounts |
| Unauthorized access to admin functions | Safe — `require_auth()` + admin check |
| Timelock bypass | Safe — `execute_pending` checks `unlock_at` against ledger timestamp |
| Re-entrancy | N/A — Soroban's execution model prevents re-entrancy |
| Storage exhaustion | Mitigated — pending transfers are cleaned up after execution/cancellation |
| Allowlist bypass | Safe — checked on every `check_transfer` and `queue_transfer` |
| Daily limit reset manipulation | Safe — uses ledger timestamp (validator consensus) |

### Dependencies

All Python dependencies are pinned to exact versions in `requirements.txt`.
The Soroban contract uses only `soroban-sdk` (pinned in `Cargo.toml`).

### Secrets

Never commit:
- `MANDATE_STELLAR_SIGNING_KEY`
- `MANDATE_ANTHROPIC_API_KEY` / `MANDATE_OPENAI_API_KEY`
- `MANDATE_JWT_SECRET`
- Any `.env` files

The `.gitignore` excludes common secret file patterns.
