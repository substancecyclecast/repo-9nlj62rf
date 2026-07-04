"""Live fiat off-ramp adapters for EMEA/Africa corridors.

Provides real API integrations with:
- Bridge.xyz: Global off-ramp (USDC→fiat, 40+ countries)
- Cowrie Exchange: Nigeria (USDC→NGN via NIBSS/NIP)
- Flutterwave: Pan-Africa (NG, KE, GH, ZA, TZ, UG)
- YellowCard: Africa crypto-to-fiat (NG, GH, KE, ZA, BW, CM)

In sandbox mode, returns deterministic quotes and mock transfer IDs.
In live mode, calls real APIs with proper authentication.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from app.adapters.base import Adapter, QuoteResult
from app.core.config import settings


@dataclass
class TransferResult:
    success: bool
    transfer_id: str
    provider: str
    status: str  # pending | processing | completed | failed
    amount_usd: float
    amount_local: float
    currency: str
    fee_usd: float
    eta: str
    reference: str = ""
    error: str = ""


class BridgeLiveAdapter(Adapter):
    """Bridge.xyz live API adapter for global stablecoin→fiat conversion."""

    name = "bridge_live"

    def quote(self, *, amount_usd: float, country: str, currency: str = "USD") -> QuoteResult:
        if not self.is_live:
            fee_rate = 0.005  # 0.5% in sandbox
            fee = round(max(0.50, amount_usd * fee_rate), 2)
            return QuoteResult(
                ok=True,
                detail=f"Bridge.xyz quote: ${amount_usd} → {currency} ({country})",
                data={
                    "provider": "bridge",
                    "amount_usd": amount_usd,
                    "fee_usd": fee,
                    "net_usd": round(amount_usd - fee, 2),
                    "currency": currency,
                    "country": country,
                    "eta": "1-2 business days",
                    "rate": 1.0,
                },
            )

        # Live: call Bridge API
        import httpx

        resp = httpx.post(
            f"{settings.bridge_api_base}/v0/transfers/quote",
            headers={"Api-Key": settings.bridge_api_key},
            json={
                "source_currency": "usdc",
                "destination_currency": currency.lower(),
                "amount": str(amount_usd),
                "destination_country": country,
            },
        )
        if resp.status_code != 200:
            return QuoteResult(ok=False, detail=f"Bridge API error: {resp.status_code}", data={})

        data = resp.json()
        return QuoteResult(
            ok=True,
            detail=f"Bridge.xyz live quote: ${amount_usd} → {currency}",
            data={
                "provider": "bridge",
                "amount_usd": amount_usd,
                "fee_usd": float(data.get("fee", 0)),
                "net_usd": float(data.get("destination_amount", amount_usd)),
                "currency": currency,
                "country": country,
                "eta": data.get("estimated_delivery", "1-2 business days"),
                "rate": float(data.get("exchange_rate", 1.0)),
                "quote_id": data.get("id", ""),
            },
        )

    def create_transfer(
        self, *, amount_usd: float, country: str, currency: str, recipient: dict
    ) -> TransferResult:
        if not self.is_live:
            tx_id = hashlib.sha256(f"bridge|{amount_usd}|{country}|{time.time()}".encode()).hexdigest()[:24]
            return TransferResult(
                success=True, transfer_id=f"bridge_{tx_id}", provider="bridge",
                status="processing", amount_usd=amount_usd, amount_local=amount_usd,
                currency=currency, fee_usd=round(amount_usd * 0.005, 2), eta="1-2 business days",
            )

        import httpx

        resp = httpx.post(
            f"{settings.bridge_api_base}/v0/transfers",
            headers={"Api-Key": settings.bridge_api_key},
            json={
                "source_currency": "usdc",
                "destination_currency": currency.lower(),
                "amount": str(amount_usd),
                "destination": recipient,
            },
        )
        data = resp.json()
        return TransferResult(
            success=resp.status_code in (200, 201),
            transfer_id=data.get("id", ""),
            provider="bridge",
            status=data.get("status", "pending"),
            amount_usd=amount_usd,
            amount_local=float(data.get("destination_amount", 0)),
            currency=currency,
            fee_usd=float(data.get("fee", 0)),
            eta=data.get("estimated_delivery", ""),
            error=data.get("error", "") if resp.status_code >= 400 else "",
        )


class CowrieAdapter(Adapter):
    """Cowrie Exchange: Nigeria USDC→NGN via NIBSS/NIP (instant)."""

    name = "cowrie"

    # Cowrie supports NGN with ~0.3% fee
    FEE_RATE = 0.003
    SUPPORTED_COUNTRIES = {"NG"}

    def quote(self, *, amount_usd: float, account_number: str = "") -> QuoteResult:
        ngn_rate = 1580.0  # Indicative USD/NGN rate (live would fetch real-time)
        fee_usd = round(max(0.25, amount_usd * self.FEE_RATE), 2)
        amount_ngn = round((amount_usd - fee_usd) * ngn_rate, 2)

        if not self.is_live:
            return QuoteResult(
                ok=True,
                detail=f"Cowrie: ${amount_usd} → ₦{amount_ngn:,.0f} via NIBSS/NIP",
                data={
                    "provider": "cowrie",
                    "amount_usd": amount_usd,
                    "amount_ngn": amount_ngn,
                    "fee_usd": fee_usd,
                    "rate_usd_ngn": ngn_rate,
                    "rail": "NIBSS/NIP",
                    "eta": "instant",
                    "country": "NG",
                },
            )

        # Live: call Cowrie API
        import httpx

        resp = httpx.post(
            f"{settings.cowrie_api_base}/v1/quotes",
            headers={"Authorization": f"Bearer {settings.cowrie_api_key}"},
            json={"amount_usd": amount_usd, "destination_currency": "NGN"},
        )
        if resp.status_code != 200:
            return QuoteResult(ok=False, detail=f"Cowrie API error: {resp.status_code}", data={})

        data = resp.json()
        return QuoteResult(
            ok=True,
            detail=f"Cowrie live: ${amount_usd} → ₦{data.get('amount_ngn', 0):,.0f}",
            data={"provider": "cowrie", **data},
        )

    def create_transfer(
        self, *, amount_usd: float, bank_code: str, account_number: str, account_name: str
    ) -> TransferResult:
        ngn_rate = 1580.0
        fee_usd = round(max(0.25, amount_usd * self.FEE_RATE), 2)
        amount_ngn = round((amount_usd - fee_usd) * ngn_rate, 2)

        if not self.is_live:
            tx_id = hashlib.sha256(f"cowrie|{account_number}|{time.time()}".encode()).hexdigest()[:20]
            return TransferResult(
                success=True, transfer_id=f"cow_{tx_id}", provider="cowrie",
                status="completed", amount_usd=amount_usd, amount_local=amount_ngn,
                currency="NGN", fee_usd=fee_usd, eta="instant",
                reference=f"NIBSS-{tx_id[:12].upper()}",
            )

        import httpx

        resp = httpx.post(
            f"{settings.cowrie_api_base}/v1/transfers",
            headers={"Authorization": f"Bearer {settings.cowrie_api_key}"},
            json={
                "amount_usd": amount_usd,
                "bank_code": bank_code,
                "account_number": account_number,
                "account_name": account_name,
            },
        )
        data = resp.json()
        return TransferResult(
            success=resp.status_code in (200, 201),
            transfer_id=data.get("id", ""),
            provider="cowrie",
            status=data.get("status", "pending"),
            amount_usd=amount_usd,
            amount_local=float(data.get("amount_ngn", 0)),
            currency="NGN",
            fee_usd=float(data.get("fee_usd", fee_usd)),
            eta="instant",
            reference=data.get("reference", ""),
            error=data.get("error", "") if resp.status_code >= 400 else "",
        )


class FlutterwaveAdapter(Adapter):
    """Flutterwave: Pan-Africa payments (NG, KE, GH, ZA, TZ, UG)."""

    name = "flutterwave"

    SUPPORTED_COUNTRIES = {"NG", "KE", "GH", "ZA", "TZ", "UG", "RW", "CM", "CI", "SN"}
    CURRENCY_MAP = {
        "NG": "NGN", "KE": "KES", "GH": "GHS", "ZA": "ZAR",
        "TZ": "TZS", "UG": "UGX", "RW": "RWF", "CM": "XAF",
        "CI": "XOF", "SN": "XOF",
    }
    FEE_RATES = {
        "NG": 0.003, "KE": 0.004, "GH": 0.005, "ZA": 0.0025,
        "TZ": 0.005, "UG": 0.005,
    }

    def quote(self, *, amount_usd: float, country: str) -> QuoteResult:
        country = country.upper()
        if country not in self.SUPPORTED_COUNTRIES:
            return QuoteResult(ok=False, detail=f"Country {country} not supported", data={})

        currency = self.CURRENCY_MAP.get(country, "USD")
        fee_rate = self.FEE_RATES.get(country, 0.005)
        fee_usd = round(max(0.25, amount_usd * fee_rate), 2)

        # Indicative rates (live would fetch from Flutterwave /rates endpoint)
        rates = {"NGN": 1580, "KES": 155, "GHS": 15.5, "ZAR": 18.2, "TZS": 2650, "UGX": 3750}
        rate = rates.get(currency, 1.0)
        amount_local = round((amount_usd - fee_usd) * rate, 2)

        return QuoteResult(
            ok=True,
            detail=f"Flutterwave: ${amount_usd} → {currency} {amount_local:,.0f} ({country})",
            data={
                "provider": "flutterwave",
                "amount_usd": amount_usd,
                "amount_local": amount_local,
                "currency": currency,
                "fee_usd": fee_usd,
                "rate": rate,
                "country": country,
                "rail": "mobile_money" if country in ("KE", "GH", "TZ", "UG") else "bank_transfer",
                "eta": "instant" if country in ("NG", "KE") else "<1 hour",
            },
        )

    def create_transfer(
        self, *, amount_usd: float, country: str, recipient: dict
    ) -> TransferResult:
        quote = self.quote(amount_usd=amount_usd, country=country)
        if not quote.ok:
            return TransferResult(
                success=False, transfer_id="", provider="flutterwave",
                status="failed", amount_usd=amount_usd, amount_local=0,
                currency="", fee_usd=0, eta="", error=quote.detail,
            )

        if not self.is_live:
            tx_id = hashlib.sha256(f"flutter|{country}|{time.time()}".encode()).hexdigest()[:20]
            return TransferResult(
                success=True, transfer_id=f"flw_{tx_id}", provider="flutterwave",
                status="processing", amount_usd=amount_usd,
                amount_local=quote.data["amount_local"],
                currency=quote.data["currency"], fee_usd=quote.data["fee_usd"],
                eta=quote.data["eta"], reference=f"FLW-{tx_id[:10].upper()}",
            )

        import httpx

        resp = httpx.post(
            f"{settings.flutterwave_api_base}/transfers",
            headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"},
            json={
                "account_bank": recipient.get("bank_code", ""),
                "account_number": recipient.get("account_number", ""),
                "amount": quote.data["amount_local"],
                "currency": quote.data["currency"],
                "narration": f"Mandate payout - {recipient.get('name', '')}",
                "reference": f"mandate-{int(time.time())}",
                "beneficiary_name": recipient.get("name", ""),
            },
        )
        data = resp.json()
        transfer_data = data.get("data", {})
        return TransferResult(
            success=data.get("status") == "success",
            transfer_id=str(transfer_data.get("id", "")),
            provider="flutterwave",
            status=transfer_data.get("status", "pending"),
            amount_usd=amount_usd,
            amount_local=float(transfer_data.get("amount", 0)),
            currency=quote.data["currency"],
            fee_usd=quote.data["fee_usd"],
            eta=quote.data["eta"],
            reference=transfer_data.get("reference", ""),
            error=data.get("message", "") if data.get("status") != "success" else "",
        )


class YellowCardAdapter(Adapter):
    """YellowCard: Africa crypto-to-fiat off-ramp."""

    name = "yellowcard"

    SUPPORTED_COUNTRIES = {"NG", "GH", "KE", "ZA", "BW", "CM", "TZ", "UG", "RW", "CI"}
    FEE_RATE = 0.005  # 0.5%

    def quote(self, *, amount_usd: float, country: str) -> QuoteResult:
        country = country.upper()
        if country not in self.SUPPORTED_COUNTRIES:
            return QuoteResult(ok=False, detail=f"Country {country} not supported", data={})

        fee_usd = round(max(0.50, amount_usd * self.FEE_RATE), 2)

        if not self.is_live:
            return QuoteResult(
                ok=True,
                detail=f"YellowCard: ${amount_usd} off-ramp to {country}",
                data={
                    "provider": "yellowcard",
                    "amount_usd": amount_usd,
                    "fee_usd": fee_usd,
                    "net_usd": round(amount_usd - fee_usd, 2),
                    "country": country,
                    "eta": "<1 hour",
                    "rail": "bank_transfer",
                },
            )

        import httpx

        headers = {
            "Authorization": f"Bearer {settings.yellowcard_api_key}",
            "X-YC-Secret": settings.yellowcard_secret_key,
        }
        resp = httpx.post(
            f"{settings.yellowcard_api_base}/quotes",
            headers=headers,
            json={"amount": amount_usd, "currency": "USD", "country": country},
        )
        if resp.status_code != 200:
            return QuoteResult(ok=False, detail=f"YellowCard error: {resp.status_code}", data={})

        data = resp.json()
        return QuoteResult(ok=True, detail="YellowCard live quote", data={"provider": "yellowcard", **data})

    def create_transfer(
        self, *, amount_usd: float, country: str, recipient: dict
    ) -> TransferResult:
        if not self.is_live:
            tx_id = hashlib.sha256(f"yc|{country}|{time.time()}".encode()).hexdigest()[:20]
            fee_usd = round(max(0.50, amount_usd * self.FEE_RATE), 2)
            return TransferResult(
                success=True, transfer_id=f"yc_{tx_id}", provider="yellowcard",
                status="processing", amount_usd=amount_usd, amount_local=amount_usd,
                currency="USD", fee_usd=fee_usd, eta="<1 hour",
                reference=f"YC-{tx_id[:10].upper()}",
            )

        import httpx

        headers = {
            "Authorization": f"Bearer {settings.yellowcard_api_key}",
            "X-YC-Secret": settings.yellowcard_secret_key,
        }
        resp = httpx.post(
            f"{settings.yellowcard_api_base}/transfers",
            headers=headers,
            json={
                "amount": amount_usd,
                "country": country,
                "recipient": recipient,
            },
        )
        data = resp.json()
        return TransferResult(
            success=resp.status_code in (200, 201),
            transfer_id=data.get("id", ""),
            provider="yellowcard",
            status=data.get("status", "pending"),
            amount_usd=amount_usd,
            amount_local=float(data.get("local_amount", 0)),
            currency=data.get("currency", ""),
            fee_usd=float(data.get("fee", 0)),
            eta="<1 hour",
            error=data.get("error", "") if resp.status_code >= 400 else "",
        )


# --- Off-ramp Router ---

def get_best_offramp(country: str) -> Adapter:
    """Select the cheapest off-ramp provider for a given country."""
    country = country.upper()

    # Nigeria: Cowrie (cheapest, instant)
    if country == "NG":
        return CowrieAdapter()

    # Pan-Africa: Flutterwave
    if country in FlutterwaveAdapter.SUPPORTED_COUNTRIES:
        return FlutterwaveAdapter()

    # Other Africa: YellowCard
    if country in YellowCardAdapter.SUPPORTED_COUNTRIES:
        return YellowCardAdapter()

    # Global fallback: Bridge.xyz
    return BridgeLiveAdapter()


# Singleton instances
bridge_live = BridgeLiveAdapter()
cowrie = CowrieAdapter()
flutterwave = FlutterwaveAdapter()
yellowcard = YellowCardAdapter()
