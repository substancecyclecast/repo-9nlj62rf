"""Asset pricing adapter.

Stablecoins are pegged ~1:1; volatile assets use indicative marks. In live mode
this would call a price oracle (Pyth/Chainlink) or a market-data API. Prices are
intentionally deterministic so reports and tests are reproducible.
"""

from __future__ import annotations

from app.adapters.base import Adapter

_INDICATIVE_USD: dict[str, float] = {
    "USDC": 1.0,
    "USDT": 1.0,
    "DAI": 1.0,
    "PYUSD": 1.0,
    "ETH": 3150.0,
    "WETH": 3150.0,
    "SOL": 152.0,
    "WBTC": 64200.0,
    "BTC": 64200.0,
}


class PricingAdapter(Adapter):
    name = "pricing"

    def price_usd(self, asset: str) -> float:
        return _INDICATIVE_USD.get(asset.upper(), 1.0)

    def value_usd(self, asset: str, amount: float) -> float:
        return round(self.price_usd(asset) * amount, 2)


pricing = PricingAdapter()
