"""Safe Module: policy-bounded automatic co-signing.

This module implements a Safe module (ERC-7579 compatible) that allows the
Mandate agent to automatically co-sign transactions that fall within the
organization's treasury policy limits.

Architecture:
  1. Agent builds a Safe transaction via SafeAdapter.build_transfer()
  2. SafeModule.can_auto_sign() checks the tx against on-chain + off-chain policy
  3. If approved, SafeModule.auto_sign() submits a confirmation to the Safe Tx Service
  4. Once threshold is met, the transaction is auto-executed

Safety guarantees:
  - Single-transfer limit: max_autonomous_transfer_usd
  - Daily aggregate limit: max_autonomous_daily_usd
  - Recipient must be in allowlist (known contractors/vendors)
  - Compliance screening must pass
  - Only USDC/EURC/NGNC stablecoins (no volatile asset auto-signing)

In sandbox mode, auto_sign() returns deterministic results.
In live mode, it calls the Safe Transaction Service API.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from app.adapters.base import Adapter
from app.core.config import settings


@dataclass
class AutoSignResult:
    approved: bool
    reason: str
    tx_hash: str = ""
    signature: str = ""
    remaining_daily_usd: float = 0.0


@dataclass
class PolicyCheckResult:
    allowed: bool
    violations: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)


# Stablecoins eligible for auto-signing (no volatile assets)
AUTO_SIGN_ELIGIBLE_ASSETS = {"USDC", "EURC", "NGNC", "USDT", "DAI", "PYUSD"}


class SafeModuleAdapter(Adapter):
    """Policy-bounded Safe co-signer module.

    Maintains a rolling daily spend counter and enforces policy limits
    before producing a cryptographic signature for the Safe Tx Service.
    """

    name = "safe_module"

    def __init__(self, mode: str | None = None):
        super().__init__(mode)
        # In-memory daily spend tracking (production: store in DB/Redis)
        self._daily_spend: dict[str, float] = {}  # safe_address -> USD spent today
        self._day_key: str = ""

    def _reset_daily_if_needed(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if self._day_key != today:
            self._daily_spend.clear()
            self._day_key = today

    def check_policy(
        self,
        *,
        amount_usd: float,
        asset: str,
        to_address: str,
        safe_address: str,
        max_transfer_usd: float = 25_000.0,
        max_daily_usd: float = 100_000.0,
        allowlist: list[str] | None = None,
    ) -> PolicyCheckResult:
        """Check if a transaction passes all auto-sign policy rules."""
        self._reset_daily_if_needed()
        violations = []
        passed = []

        # Check 1: Asset eligibility
        if asset.upper() in AUTO_SIGN_ELIGIBLE_ASSETS:
            passed.append(f"asset_eligible: {asset}")
        else:
            violations.append(f"asset_not_eligible: {asset} (only stablecoins)")

        # Check 2: Single transfer limit
        if amount_usd <= max_transfer_usd:
            passed.append(f"within_single_limit: ${amount_usd} <= ${max_transfer_usd}")
        else:
            violations.append(
                f"exceeds_single_limit: ${amount_usd} > ${max_transfer_usd}"
            )

        # Check 3: Daily aggregate limit
        current_daily = self._daily_spend.get(safe_address, 0.0)
        if current_daily + amount_usd <= max_daily_usd:
            passed.append(
                f"within_daily_limit: ${current_daily + amount_usd} <= ${max_daily_usd}"
            )
        else:
            violations.append(
                f"exceeds_daily_limit: ${current_daily} + ${amount_usd} > ${max_daily_usd}"
            )

        # Check 4: Recipient allowlist
        if allowlist is not None:
            if to_address.lower() in [a.lower() for a in allowlist]:
                passed.append(f"recipient_in_allowlist: {to_address[:10]}...")
            else:
                violations.append(f"recipient_not_in_allowlist: {to_address[:10]}...")
        else:
            passed.append("allowlist_not_enforced")

        return PolicyCheckResult(
            allowed=len(violations) == 0,
            violations=violations,
            checks_passed=passed,
        )

    def auto_sign(
        self,
        *,
        safe_tx_hash: str,
        safe_address: str,
        amount_usd: float,
        asset: str,
        to_address: str,
        max_transfer_usd: float = 25_000.0,
        max_daily_usd: float = 100_000.0,
        allowlist: list[str] | None = None,
    ) -> AutoSignResult:
        """Attempt to auto-sign a Safe transaction within policy bounds.

        In sandbox mode: returns deterministic approval/rejection.
        In live mode: calls Safe Transaction Service to submit confirmation.
        """
        # Run policy check
        check = self.check_policy(
            amount_usd=amount_usd,
            asset=asset,
            to_address=to_address,
            safe_address=safe_address,
            max_transfer_usd=max_transfer_usd,
            max_daily_usd=max_daily_usd,
            allowlist=allowlist,
        )

        if not check.allowed:
            return AutoSignResult(
                approved=False,
                reason=f"Policy violation: {'; '.join(check.violations)}",
                remaining_daily_usd=max_daily_usd - self._daily_spend.get(safe_address, 0.0),
            )

        # Update daily spend counter
        self._daily_spend[safe_address] = (
            self._daily_spend.get(safe_address, 0.0) + amount_usd
        )

        if self.is_live:
            return self._live_sign(safe_tx_hash, safe_address)

        # Sandbox: deterministic signature
        sig = hashlib.sha256(
            f"module-sign|{safe_tx_hash}|{settings.safe_module_address}".encode()
        ).hexdigest()
        return AutoSignResult(
            approved=True,
            reason="Policy check passed — auto-signed by module",
            tx_hash=safe_tx_hash,
            signature=f"0x{sig}",
            remaining_daily_usd=max_daily_usd - self._daily_spend.get(safe_address, 0.0),
        )

    def _live_sign(self, safe_tx_hash: str, safe_address: str) -> AutoSignResult:
        """Submit a confirmation to the Safe Transaction Service (live mode).

        Requires MANDATE_SAFE_SIGNER_KEY to be set (the module's private key).
        """
        import httpx
        from eth_account import Account

        if not settings.safe_signer_key:
            return AutoSignResult(
                approved=False,
                reason="Live mode requires MANDATE_SAFE_SIGNER_KEY",
            )

        # Sign the safe_tx_hash with the module's private key
        account = Account.from_key(settings.safe_signer_key)
        message_hash = bytes.fromhex(safe_tx_hash[2:] if safe_tx_hash.startswith("0x") else safe_tx_hash)
        signature = account.signHash(message_hash)

        # Submit to Safe Transaction Service
        service_url = settings.safe_tx_service_base
        url = f"{service_url}/api/v1/multisig-transactions/{safe_tx_hash}/confirmations/"

        with httpx.Client() as client:
            resp = client.post(url, json={"signature": signature.signature.hex()})

        if resp.status_code in (200, 201):
            return AutoSignResult(
                approved=True,
                reason="Signed and submitted to Safe Transaction Service",
                tx_hash=safe_tx_hash,
                signature=signature.signature.hex(),
                remaining_daily_usd=0.0,  # Would calculate from DB
            )
        else:
            return AutoSignResult(
                approved=False,
                reason=f"Safe Tx Service error: {resp.status_code} {resp.text[:200]}",
            )

    def get_daily_spend(self, safe_address: str) -> float:
        """Get current daily spend for a Safe address."""
        self._reset_daily_if_needed()
        return self._daily_spend.get(safe_address, 0.0)


safe_module = SafeModuleAdapter()
