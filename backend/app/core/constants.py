"""Shared enums and domain constants used across the platform."""

from __future__ import annotations

from enum import StrEnum


class Chain(StrEnum):
    ETHEREUM = "ethereum"
    BASE = "base"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    POLYGON = "polygon"
    SOLANA = "solana"
    STELLAR = "stellar"


EVM_CHAINS = {Chain.ETHEREUM, Chain.BASE, Chain.ARBITRUM, Chain.OPTIMISM, Chain.POLYGON}
STELLAR_CHAINS = {Chain.STELLAR}

# Indicative chain ids for EVM networks (used by Safe / Li.Fi adapters).
CHAIN_IDS: dict[Chain, int] = {
    Chain.ETHEREUM: 1,
    Chain.BASE: 8453,
    Chain.ARBITRUM: 42161,
    Chain.OPTIMISM: 10,
    Chain.POLYGON: 137,
}

# Indicative per-transfer settlement cost in USD, used by the cheapest-chain
# routing heuristic. Solana and L2s are dramatically cheaper than mainnet.
CHAIN_TX_COST_USD: dict[Chain, float] = {
    Chain.ETHEREUM: 6.20,
    Chain.BASE: 0.012,
    Chain.ARBITRUM: 0.030,
    Chain.OPTIMISM: 0.025,
    Chain.POLYGON: 0.004,
    Chain.SOLANA: 0.0008,
    Chain.STELLAR: 0.00001,  # ~100 stroops, cheapest cross-border rail
}


class Stablecoin(StrEnum):
    USDC = "USDC"
    USDT = "USDT"
    DAI = "DAI"
    PYUSD = "PYUSD"
    EURC = "EURC"  # EUR stablecoin on Stellar — key for MiCA/EMEA
    NGNC = "NGNC"  # NGN-backed stablecoin on Stellar for Africa payroll


class TxType(StrEnum):
    DEPOSIT = "deposit"
    PAYOUT = "payout"
    PAYROLL = "payroll"
    VENDOR = "vendor"
    SWAP = "swap"
    YIELD_DEPOSIT = "yield_deposit"
    YIELD_WITHDRAW = "yield_withdraw"
    OFFRAMP = "offramp"
    FEE = "fee"
    INTERNAL = "internal"


class TxStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    AWAITING_SIGNATURES = "awaiting_signatures"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


# Default double-entry chart of accounts seeded for every organization.
DEFAULT_CHART_OF_ACCOUNTS: list[tuple[str, str, AccountType]] = [
    ("1000", "Treasury — Stablecoins", AccountType.ASSET),
    ("1010", "Treasury — Volatile Assets", AccountType.ASSET),
    ("1100", "Yield Positions", AccountType.ASSET),
    ("1200", "Fiat Bank (off-ramp)", AccountType.ASSET),
    ("2000", "Accounts Payable", AccountType.LIABILITY),
    ("2100", "Accrued Payroll", AccountType.LIABILITY),
    ("3000", "Contributed Capital", AccountType.EQUITY),
    ("3900", "Retained Earnings", AccountType.EQUITY),
    ("4000", "Protocol Revenue", AccountType.REVENUE),
    ("4100", "Yield Income", AccountType.REVENUE),
    ("5000", "Contractor & Payroll Expense", AccountType.EXPENSE),
    ("5100", "Vendor & Software Expense", AccountType.EXPENSE),
    ("5200", "Network & Transaction Fees", AccountType.EXPENSE),
    ("5300", "FX & Swap Spread", AccountType.EXPENSE),
    ("1300", "RWA — Tokenized T-Bills (Stellar)", AccountType.ASSET),
    ("1310", "RWA — Tokenized Real Estate", AccountType.ASSET),
]
