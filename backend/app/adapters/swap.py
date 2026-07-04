"""Cross-chain / cross-asset swap adapter (Li.Fi style aggregator).

Used by the agent to convert between stablecoins or bridge assets to the
cheapest settlement chain. Sandbox mode applies a realistic spread; live mode
would call the Li.Fi `/quote` and `/status` endpoints.
"""

from __future__ import annotations

from app.adapters.base import Adapter, QuoteResult
from app.adapters.pricing import pricing

# Indicative spread in basis points by route quality.
_SPREAD_BPS = {
    ("USDC", "USDT"): 4,
    ("USDT", "USDC"): 4,
    ("USDC", "DAI"): 6,
    ("DAI", "USDC"): 6,
    ("ETH", "USDC"): 18,
    ("SOL", "USDC"): 22,
}


class SwapAdapter(Adapter):
    name = "lifi"

    def quote(
        self, *, from_asset: str, to_asset: str, amount: float, from_chain: str, to_chain: str
    ) -> QuoteResult:
        from_asset, to_asset = from_asset.upper(), to_asset.upper()
        in_usd = pricing.value_usd(from_asset, amount)
        bps = _SPREAD_BPS.get((from_asset, to_asset), 12)
        if from_chain != to_chain:
            bps += 6  # bridging premium
        spread_usd = round(in_usd * bps / 10_000, 2)
        out_usd = in_usd - spread_usd
        to_amount = round(out_usd / pricing.price_usd(to_asset), 6)
        return QuoteResult(
            ok=True,
            detail=f"{amount} {from_asset}@{from_chain} -> {to_amount} {to_asset}@{to_chain}",
            data={
                "from_asset": from_asset,
                "to_asset": to_asset,
                "from_chain": from_chain,
                "to_chain": to_chain,
                "from_amount": amount,
                "to_amount": to_amount,
                "in_usd": in_usd,
                "out_usd": out_usd,
                "spread_bps": bps,
                "spread_usd": spread_usd,
                "tool": "lifi",
            },
        )


swap = SwapAdapter()
