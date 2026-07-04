"""Transaction auto-categorization.

Rule-based keyword matching over counterparty + memo, with a sensible fallback
by transaction type. In live deployments this is the first pass before an LLM
handles the long tail; the rules alone resolve the vast majority of entries.
"""

from __future__ import annotations

from app.core.constants import TxType

_KEYWORD_RULES: list[tuple[tuple[str, ...], str]] = [
    (("payroll", "salary", "contractor", "wage"), "payroll"),
    (("aws", "gcp", "azure", "vercel", "github", "datadog", "openai", "anthropic", "saas"),
     "software"),
    (("aave", "morpho", "ondo", "yield", "staking", "t-bill"), "yield"),
    (("swap", "lifi", "bridge", "convert"), "swap"),
    (("gas", "network fee", "priority fee"), "network_fees"),
    (("legal", "deloitte", "audit", "kpmg", "counsel"), "professional_services"),
    (("marketing", "ads", "sponsorship", "grant"), "marketing"),
    (("rent", "office", "wework"), "facilities"),
]

_TYPE_FALLBACK = {
    TxType.PAYROLL.value: "payroll",
    TxType.VENDOR.value: "vendor",
    TxType.SWAP.value: "swap",
    TxType.YIELD_DEPOSIT.value: "yield",
    TxType.YIELD_WITHDRAW.value: "yield",
    TxType.FEE.value: "network_fees",
    TxType.OFFRAMP.value: "payroll",
    TxType.DEPOSIT.value: "revenue",
}


def categorize(*, counterparty: str = "", memo: str = "", tx_type: str = "") -> str:
    haystack = f"{counterparty} {memo}".lower()
    for keywords, category in _KEYWORD_RULES:
        if any(k in haystack for k in keywords):
            return category
    return _TYPE_FALLBACK.get(tx_type, "uncategorized")
