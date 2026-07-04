"""Yield venue adapter (Aave v3, Morpho, tokenized T-bills, Stellar RWA).

Surfaces current APYs and supports deposit/withdraw of idle treasury under the
organization's policy. Sandbox APYs are indicative and deterministic.

Includes Stellar-native RWA venues (tokenized US T-bills, EMEA government bonds)
via Soroban smart contracts and Stellar asset issuance.
"""

from __future__ import annotations

from app.adapters.base import Adapter

# venue -> (asset, chain, apy, risk_tier)
_VENUES = {
    "aave_v3_usdc": ("USDC", "base", 0.0512, "low"),
    "morpho_usdc": ("USDC", "base", 0.0648, "low-mid"),
    "ondo_ousg": ("USDC", "ethereum", 0.0489, "t-bill"),
    "aave_v3_usdt": ("USDT", "arbitrum", 0.0473, "low"),
    # Stellar RWA venues — tokenized real-world assets
    "stellar_tbill_us": ("USDC", "stellar", 0.0525, "t-bill"),
    "stellar_tbill_eu": ("EURC", "stellar", 0.0380, "t-bill"),
    "stellar_ultrashort_bond": ("USDC", "stellar", 0.0465, "low"),
    "stellar_emea_mmf": ("USDC", "stellar", 0.0410, "low"),
}

# Detailed venue metadata for Stellar RWA products.
STELLAR_RWA_VENUES = {
    "stellar_tbill_us": {
        "name": "US Treasury Bills (tokenized on Stellar)",
        "issuer": "Franklin Templeton / Ondo via Stellar",
        "asset_code": "USTB",
        "soroban_contract": "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
        "maturity": "3-month rolling",
        "min_investment_usd": 1_000,
        "regulatory": "SEC-registered, MiCA-compliant tokenized security",
        "custody": "Qualified custodian (BitGo / Anchorage)",
    },
    "stellar_tbill_eu": {
        "name": "EU Government Bonds (tokenized on Stellar)",
        "issuer": "ECB-eligible issuer via Stellar",
        "asset_code": "EUGB",
        "soroban_contract": "CBLDHNONTQSGJOUFAMC44ZZL2ZXOTQZEKZ3KXIT2HKPXGT7FUQIGXWZ",
        "maturity": "6-month rolling",
        "min_investment_usd": 5_000,
        "regulatory": "MiCA-compliant, ESMA-supervised tokenized security",
        "custody": "Qualified EU custodian",
    },
    "stellar_ultrashort_bond": {
        "name": "Ultra-Short Duration Bond Fund (Stellar)",
        "issuer": "Tokenized via Soroban smart contract",
        "asset_code": "USBF",
        "soroban_contract": "CDYGXAEIWL5N2HPFKGLQXURZZZQ5TWNLVV5QDOTWNQGKXJ5V3PFXXLA",
        "maturity": "1-month rolling",
        "min_investment_usd": 10_000,
        "regulatory": "Reg D exempt, MiCA pilot regime",
    },
    "stellar_emea_mmf": {
        "name": "EMEA Money Market Fund (Stellar-native)",
        "issuer": "EMEA-regulated MMF via Stellar",
        "asset_code": "EMMF",
        "soroban_contract": "CAKQDVWL7N2HPFKGLQXURZZZQ5TWNLVV5QDOTWNGKXJ5VRABC123456",
        "maturity": "Daily liquidity",
        "min_investment_usd": 5_000,
        "regulatory": "MiCA Art. 44 compliant, UCITS eligible",
    },
}


class YieldAdapter(Adapter):
    name = "yield"

    def list_venues(self, asset: str | None = None) -> list[dict]:
        out = []
        for venue, (vasset, chain, apy, risk) in _VENUES.items():
            if asset and vasset != asset.upper():
                continue
            entry = {
                "venue": venue,
                "asset": vasset,
                "chain": chain,
                "apy": apy,
                "risk_tier": risk,
            }
            # Add RWA metadata for Stellar venues
            if venue in STELLAR_RWA_VENUES:
                entry["rwa_metadata"] = STELLAR_RWA_VENUES[venue]
            out.append(entry)
        return sorted(out, key=lambda v: v["apy"], reverse=True)

    def list_stellar_rwa(self) -> list[dict]:
        """List only Stellar-native RWA yield venues."""
        return [
            {
                "venue": venue,
                "asset": _VENUES[venue][0],
                "chain": "stellar",
                "apy": _VENUES[venue][2],
                "risk_tier": _VENUES[venue][3],
                "rwa_metadata": meta,
            }
            for venue, meta in STELLAR_RWA_VENUES.items()
        ]

    def best_venue(self, asset: str = "USDC") -> dict | None:
        venues = self.list_venues(asset)
        return venues[0] if venues else None

    def best_stellar_venue(self, asset: str = "USDC") -> dict | None:
        """Best yield venue on Stellar specifically."""
        venues = [v for v in self.list_venues(asset) if v["chain"] == "stellar"]
        return venues[0] if venues else None

    def project_annual_income(self, principal_usd: float, apy: float) -> float:
        return round(principal_usd * apy, 2)


yield_adapter = YieldAdapter()
