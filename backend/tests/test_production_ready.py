"""Tests for production-ready features: auth, safe module, live off-ramp, config."""

from __future__ import annotations

import pytest


# --- Config tests ---

def test_config_has_all_live_keys():
    """Verify all production config keys exist with defaults."""
    from app.core.config import settings

    assert settings.integration_mode == "sandbox"
    assert settings.stellar_network == "testnet"
    assert settings.stellar_horizon_url.startswith("https://")
    assert settings.stellar_soroban_rpc.startswith("https://")
    assert settings.auth_enabled is False
    assert settings.jwt_algorithm == "HS256"
    assert settings.bridge_api_base == "https://api.bridge.xyz"
    assert settings.cowrie_api_base == "https://api.cowrie.exchange"
    assert settings.flutterwave_api_base == "https://api.flutterwave.com/v3"
    assert settings.yellowcard_api_base == "https://api.yellowcard.io/v1"
    assert settings.safe_tx_service_base.startswith("https://")


def test_config_live_mode_switch():
    """Config can be set to live mode."""
    from app.core.config import Settings

    s = Settings(integration_mode="live", stellar_network="public")
    assert s.integration_mode == "live"
    assert s.stellar_is_mainnet is True


# --- Auth tests ---

def test_auth_role_permissions():
    """RBAC roles have correct permissions."""
    from app.core.auth import AuthUser, Role

    owner = AuthUser(user_id="u1", org_id=1, role=Role.OWNER)
    assert owner.has_permission("treasury:read")
    assert owner.has_permission("settings:write")
    assert owner.has_permission("anything:at:all")

    viewer = AuthUser(user_id="u2", org_id=1, role=Role.VIEWER)
    assert viewer.has_permission("treasury:read")
    assert not viewer.has_permission("treasury:write")
    assert not viewer.has_permission("payroll:execute")

    agent = AuthUser(user_id="u3", org_id=1, role=Role.AGENT)
    assert agent.has_permission("agent:execute")
    assert agent.has_permission("payroll:execute")
    assert not agent.has_permission("settings:write")


def test_auth_user_require_permission():
    """require_permission raises on denied actions."""
    from fastapi import HTTPException
    from app.core.auth import AuthUser, Role

    member = AuthUser(user_id="u1", org_id=1, role=Role.MEMBER)
    member.require_permission("treasury:read")  # Should not raise

    with pytest.raises(HTTPException) as exc_info:
        member.require_permission("settings:write")
    assert exc_info.value.status_code == 403


def test_jwt_encode_decode():
    """JWT encode → decode roundtrip works."""
    from app.core.auth import _encode_jwt, _decode_jwt

    payload = {"sub": "user-123", "org_id": 1, "role": "admin", "email": "a@b.com", "exp": 9999999999}
    token = _encode_jwt(payload)
    decoded = _decode_jwt(token)
    assert decoded["sub"] == "user-123"
    assert decoded["org_id"] == 1
    assert decoded["role"] == "admin"


def test_jwt_expired_token():
    """Expired JWT is rejected."""
    from fastapi import HTTPException
    from app.core.auth import _encode_jwt, _decode_jwt

    payload = {"sub": "user-123", "org_id": 1, "role": "admin", "exp": 1}  # long expired
    token = _encode_jwt(payload)
    with pytest.raises(HTTPException) as exc_info:
        _decode_jwt(token)
    assert exc_info.value.status_code == 401


# --- Safe Module tests ---

def test_safe_module_policy_check_passes():
    """Safe module approves valid transactions."""
    from app.adapters.safe_module import SafeModuleAdapter

    module = SafeModuleAdapter(mode="sandbox")
    result = module.check_policy(
        amount_usd=5000.0,
        asset="USDC",
        to_address="0x1234567890abcdef",
        safe_address="0xSafe1",
        max_transfer_usd=25000.0,
        max_daily_usd=100000.0,
    )
    assert result.allowed
    assert len(result.violations) == 0


def test_safe_module_rejects_over_limit():
    """Safe module rejects single transaction over limit."""
    from app.adapters.safe_module import SafeModuleAdapter

    module = SafeModuleAdapter(mode="sandbox")
    result = module.check_policy(
        amount_usd=30000.0,
        asset="USDC",
        to_address="0x1234567890abcdef",
        safe_address="0xSafe1",
        max_transfer_usd=25000.0,
        max_daily_usd=100000.0,
    )
    assert not result.allowed
    assert any("exceeds_single_limit" in v for v in result.violations)


def test_safe_module_rejects_volatile_asset():
    """Safe module rejects volatile (non-stablecoin) assets."""
    from app.adapters.safe_module import SafeModuleAdapter

    module = SafeModuleAdapter(mode="sandbox")
    result = module.check_policy(
        amount_usd=1000.0,
        asset="ETH",
        to_address="0x1234567890abcdef",
        safe_address="0xSafe1",
    )
    assert not result.allowed
    assert any("not_eligible" in v for v in result.violations)


def test_safe_module_daily_limit():
    """Safe module enforces daily aggregate limit."""
    from app.adapters.safe_module import SafeModuleAdapter

    module = SafeModuleAdapter(mode="sandbox")
    # First: $20k — within both $25k single and $50k daily
    r1 = module.auto_sign(
        safe_tx_hash="0xabc", safe_address="0xSafe1",
        amount_usd=20000.0, asset="USDC", to_address="0x123",
        max_transfer_usd=25000.0, max_daily_usd=50000.0,
    )
    assert r1.approved

    # Second: $20k — within single but total $40k still < $50k daily
    r2 = module.auto_sign(
        safe_tx_hash="0xdef", safe_address="0xSafe1",
        amount_usd=20000.0, asset="USDC", to_address="0x123",
        max_transfer_usd=25000.0, max_daily_usd=50000.0,
    )
    assert r2.approved

    # Third: $20k — total $60k > $50k daily
    r3 = module.auto_sign(
        safe_tx_hash="0xghi", safe_address="0xSafe1",
        amount_usd=20000.0, asset="USDC", to_address="0x123",
        max_transfer_usd=25000.0, max_daily_usd=50000.0,
    )
    assert not r3.approved
    assert "daily_limit" in r3.reason


def test_safe_module_allowlist():
    """Safe module enforces recipient allowlist."""
    from app.adapters.safe_module import SafeModuleAdapter

    module = SafeModuleAdapter(mode="sandbox")
    result = module.check_policy(
        amount_usd=1000.0,
        asset="USDC",
        to_address="0xUnknown",
        safe_address="0xSafe1",
        allowlist=["0xAllowed1", "0xAllowed2"],
    )
    assert not result.allowed
    assert any("not_in_allowlist" in v for v in result.violations)


# --- Live Off-ramp tests ---

def test_cowrie_quote():
    """Cowrie returns valid NGN quote."""
    from app.adapters.live_offramp import CowrieAdapter

    adapter = CowrieAdapter(mode="sandbox")
    quote = adapter.quote(amount_usd=1000.0)
    assert quote.ok
    assert quote.data["country"] == "NG"
    assert quote.data["fee_usd"] > 0
    assert quote.data["amount_ngn"] > 0


def test_cowrie_transfer():
    """Cowrie transfer returns success in sandbox."""
    from app.adapters.live_offramp import CowrieAdapter

    adapter = CowrieAdapter(mode="sandbox")
    result = adapter.create_transfer(
        amount_usd=500.0,
        bank_code="058",
        account_number="0012345678",
        account_name="John Doe",
    )
    assert result.success
    assert result.provider == "cowrie"
    assert result.currency == "NGN"
    assert result.transfer_id.startswith("cow_")


def test_flutterwave_quote_nigeria():
    """Flutterwave returns valid NGN quote."""
    from app.adapters.live_offramp import FlutterwaveAdapter

    adapter = FlutterwaveAdapter(mode="sandbox")
    quote = adapter.quote(amount_usd=1000.0, country="NG")
    assert quote.ok
    assert quote.data["currency"] == "NGN"
    assert quote.data["amount_local"] > 0


def test_flutterwave_quote_kenya():
    """Flutterwave returns valid KES quote."""
    from app.adapters.live_offramp import FlutterwaveAdapter

    adapter = FlutterwaveAdapter(mode="sandbox")
    quote = adapter.quote(amount_usd=500.0, country="KE")
    assert quote.ok
    assert quote.data["currency"] == "KES"
    assert quote.data["rail"] == "mobile_money"


def test_flutterwave_unsupported_country():
    """Flutterwave rejects unsupported country."""
    from app.adapters.live_offramp import FlutterwaveAdapter

    adapter = FlutterwaveAdapter(mode="sandbox")
    quote = adapter.quote(amount_usd=500.0, country="JP")
    assert not quote.ok


def test_yellowcard_quote():
    """YellowCard returns valid quote for Nigeria."""
    from app.adapters.live_offramp import YellowCardAdapter

    adapter = YellowCardAdapter(mode="sandbox")
    quote = adapter.quote(amount_usd=1000.0, country="NG")
    assert quote.ok
    assert quote.data["provider"] == "yellowcard"


def test_get_best_offramp_routing():
    """Off-ramp router selects cheapest provider per country."""
    from app.adapters.live_offramp import get_best_offramp, CowrieAdapter, FlutterwaveAdapter, BridgeLiveAdapter

    assert isinstance(get_best_offramp("NG"), CowrieAdapter)
    assert isinstance(get_best_offramp("KE"), FlutterwaveAdapter)
    assert isinstance(get_best_offramp("GH"), FlutterwaveAdapter)
    assert isinstance(get_best_offramp("US"), BridgeLiveAdapter)
    assert isinstance(get_best_offramp("JP"), BridgeLiveAdapter)


def test_bridge_live_quote():
    """Bridge.xyz returns valid quote in sandbox."""
    from app.adapters.live_offramp import BridgeLiveAdapter

    adapter = BridgeLiveAdapter(mode="sandbox")
    quote = adapter.quote(amount_usd=5000.0, country="US", currency="USD")
    assert quote.ok
    assert quote.data["provider"] == "bridge"
    assert quote.data["fee_usd"] > 0


# --- Live mode adapters ---

def test_safe_adapter_sandbox():
    """SafeAdapter in sandbox returns deterministic results."""
    from app.adapters.chains import SafeAdapter

    adapter = SafeAdapter(mode="sandbox")
    result = adapter.build_transfer(
        chain="base", safe_address="0xSafe", to="0xRecipient",
        asset="USDC", amount=1000.0, nonce=1
    )
    assert result["type"] == "safe_multisig_tx"
    assert result["safe_tx_hash"].startswith("0x")
    assert "live" not in result


def test_stellar_adapter_sandbox():
    """StellarAdapter in sandbox returns deterministic results."""
    from app.adapters.chains import StellarAdapter

    adapter = StellarAdapter(mode="sandbox")
    result = adapter.build_transfer(
        account="GABCDEFGH" * 7 + "AB",  # 56 chars
        to="GZYXWVUTS" * 7 + "AB",
        asset="USDC", amount=500.0, sequence=1
    )
    assert result["type"] == "stellar_multisig_tx"
    assert result["network"] == "testnet"
