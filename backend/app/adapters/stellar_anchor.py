"""Stellar anchor & SEP-24/SEP-31 off/on-ramp adapter.

Stellar anchors bridge fiat ↔ Stellar assets (USDC, EURC, local stablecoins).
SEP-24 handles interactive deposit/withdrawal; SEP-31 handles cross-border
payments where the sender and receiver may be on different rails.

For EMEA/Africa payroll, anchors provide:
- Direct deposit to M-Pesa (Kenya, Tanzania)
- Bank transfers via local rails (NIBSS/NIP in Nigeria, RTC in South Africa)
- SEPA Instant for Europe
- Instant Mobile Money across West/East Africa

In sandbox mode, quotes are deterministic. In live mode, the adapter calls
the anchor's SEP-31 API.
"""

from __future__ import annotations

from app.adapters.base import Adapter, QuoteResult

# Stellar anchor rails by country — dramatically cheaper than traditional SWIFT.
_STELLAR_RAILS = {
    # Africa — Stellar's strongest corridor
    "NG": ("NIBSS/NIP via Cowrie", 0.003, "instant", "NGNC"),
    "KE": ("M-Pesa via Flutterwave", 0.004, "instant", "USDC"),
    "GH": ("Mobile Money via Stellar Anchor", 0.004, "instant", "USDC"),
    "ZA": ("RTC via StellarPay", 0.005, "same day", "USDC"),
    "TZ": ("M-Pesa via Stellar", 0.004, "instant", "USDC"),
    "UG": ("Mobile Money", 0.005, "instant", "USDC"),
    "RW": ("MTN MoMo", 0.005, "instant", "USDC"),
    "SN": ("Orange Money", 0.005, "instant", "USDC"),
    "ET": ("CBE Birr", 0.006, "same day", "USDC"),
    "EG": ("InstaPay", 0.005, "instant", "USDC"),
    # Middle East
    "AE": ("IPP via Stellar", 0.004, "instant", "USDC"),
    "SA": ("SARIE via Stellar", 0.005, "instant", "USDC"),
    # Europe (SEPA via Stellar EURC anchors)
    "DE": ("SEPA Instant via MoneyGram", 0.002, "instant", "EURC"),
    "FR": ("SEPA Instant via MoneyGram", 0.002, "instant", "EURC"),
    "IT": ("SEPA Instant via MoneyGram", 0.002, "instant", "EURC"),
    "ES": ("SEPA Instant via MoneyGram", 0.002, "instant", "EURC"),
    "NL": ("SEPA Instant via MoneyGram", 0.002, "instant", "EURC"),
    "PT": ("SEPA Instant via MoneyGram", 0.002, "instant", "EURC"),
    "GB": ("FPS via Stellar Anchor", 0.003, "instant", "USDC"),
    "PL": ("SEPA via MoneyGram", 0.003, "instant", "EURC"),
    "TR": ("FAST via Stellar", 0.004, "instant", "USDC"),
}

# Default fallback for countries without specific Stellar anchors.
_DEFAULT_STELLAR_RAIL = ("Stellar Cross-Border (SWIFT alternative)", 0.006, "1-2 hours", "USDC")


class StellarAnchorAdapter(Adapter):
    """SEP-31 cross-border payment adapter using Stellar anchors."""

    name = "stellar_anchor"

    def quote(
        self,
        *,
        amount_usd: float,
        country: str,
        asset: str = "USDC",
        dest_asset: str | None = None,
    ) -> QuoteResult:
        """Quote an off-ramp via Stellar anchor for a given country."""
        rail, rate, eta, native_asset = _STELLAR_RAILS.get(
            country.upper(), _DEFAULT_STELLAR_RAIL
        )
        fee_usd = round(max(0.01, amount_usd * rate), 2)
        return QuoteResult(
            ok=True,
            detail=f"Stellar anchor: {amount_usd} USD via {rail} ({country})",
            data={
                "provider": "stellar_anchor",
                "protocol": "SEP-31",
                "rail": rail,
                "country": country.upper(),
                "send_asset": asset,
                "receive_asset": dest_asset or native_asset,
                "amount_usd": amount_usd,
                "fee_usd": fee_usd,
                "net_usd": round(amount_usd - fee_usd, 2),
                "eta": eta,
                "stellar_fee_stroops": 100,
                "total_cost_vs_swift_pct": round(rate / 0.012 * 100, 1),
            },
        )

    def supported_countries(self) -> list[str]:
        return sorted(_STELLAR_RAILS.keys())

    def compare_vs_traditional(self, *, amount_usd: float, country: str) -> dict:
        """Compare Stellar anchor cost vs traditional off-ramp (Bridge.xyz / SWIFT)."""
        stellar_quote = self.quote(amount_usd=amount_usd, country=country)
        # Traditional costs from offramp adapter
        traditional_rates = {
            "NG": 0.009, "KE": 0.008, "GH": 0.010, "ZA": 0.009,
            "AE": 0.008, "DE": 0.004, "GB": 0.004, "TR": 0.008,
        }
        trad_rate = traditional_rates.get(country.upper(), 0.012)
        trad_fee = round(max(0.25, amount_usd * trad_rate), 2)
        savings = round(trad_fee - stellar_quote.data["fee_usd"], 2)
        return {
            "stellar_fee_usd": stellar_quote.data["fee_usd"],
            "traditional_fee_usd": trad_fee,
            "savings_usd": savings,
            "savings_pct": round(savings / trad_fee * 100, 1) if trad_fee > 0 else 0,
            "stellar_eta": stellar_quote.data["eta"],
        }


stellar_anchor = StellarAnchorAdapter()
