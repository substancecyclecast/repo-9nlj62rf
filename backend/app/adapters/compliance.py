"""KYC/AML compliance adapter (Bridge / Brale style).

Screens payees before payout. Sandbox uses deterministic rules (sanctioned
country list + simple heuristics) so compliance gating is demonstrable without
a live provider. Live mode would call the provider's screening API.
"""

from __future__ import annotations

from app.adapters.base import Adapter

# Illustrative restricted jurisdictions for sandbox screening.
_RESTRICTED = {"KP", "IR", "SY", "CU"}


class ComplianceAdapter(Adapter):
    name = "compliance"

    def screen(self, *, name: str, country: str, wallet_address: str = "") -> dict:
        country = (country or "").upper()
        if country in _RESTRICTED:
            return {
                "status": "flagged",
                "reason": f"Restricted jurisdiction: {country}",
                "cleared": False,
            }
        if wallet_address and not (
            wallet_address.startswith("0x") or len(wallet_address) >= 32
        ):
            return {
                "status": "flagged",
                "reason": "Malformed payout address",
                "cleared": False,
            }
        return {"status": "cleared", "reason": "Passed sandbox screening", "cleared": True}


compliance = ComplianceAdapter()
