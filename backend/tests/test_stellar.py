"""Tests for Stellar integration: chain adapter, routing, anchor, Soroban policy, RWA."""


from app.adapters.chains import StellarAdapter, get_chain_adapter
from app.adapters.soroban_policy import soroban_policy
from app.adapters.stellar_anchor import stellar_anchor
from app.adapters.yield_venues import yield_adapter
from app.core.constants import Chain
from app.services.routing import (
    STELLAR_PREFERRED_COUNTRIES,
    cheapest_chain,
    is_stellar_address,
    select_route,
)


STELLAR_G_ADDR = "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOBD3XYDSM7IBWA3"
STELLAR_C_ADDR = "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC"
STELLAR_PAYEE = "GAISHA7BELLO0STELLAR0000000000000000000000000000NGPAY000"


class TestStellarAdapter:
    def test_build_transfer(self):
        adapter = StellarAdapter()
        tx = adapter.build_transfer(
            account=STELLAR_G_ADDR,
            to=STELLAR_PAYEE,
            asset="USDC",
            amount=5000.0,
            sequence=12345,
            memo="Payroll NG",
        )
        assert tx["type"] == "stellar_multisig_tx"
        assert tx["chain"] == Chain.STELLAR
        assert tx["amount"] == 5000.0
        assert tx["fee_stroops"] == 100
        assert tx["tx_hash"].startswith("stellar_")

    def test_build_soroban_invoke(self):
        adapter = StellarAdapter()
        tx = adapter.build_soroban_invoke(
            account=STELLAR_G_ADDR,
            contract_id=STELLAR_C_ADDR,
            function_name="check_transfer",
            args=[{"type": "u128", "value": "5000"}],
            sequence=12346,
        )
        assert tx["type"] == "soroban_invoke"
        assert tx["function"] == "check_transfer"
        assert tx["tx_hash"].startswith("soroban_")

    def test_execute(self):
        adapter = StellarAdapter()
        result = adapter.execute(safe_tx_hash="stellar_abc123")
        assert result["executed"] is True
        assert isinstance(result["ledger"], int)
        assert result["fee_charged_stroops"] == 100

    def test_build_path_payment(self):
        adapter = StellarAdapter()
        tx = adapter.build_path_payment(
            account=STELLAR_G_ADDR,
            to=STELLAR_PAYEE,
            send_asset="USDC",
            dest_asset="NGNC",
            send_amount=5000.0,
            dest_min=4950.0,
            sequence=12347,
        )
        assert tx["type"] == "stellar_path_payment"
        assert tx["send_asset"] == "USDC"
        assert tx["dest_asset"] == "NGNC"

    def test_get_chain_adapter_stellar(self):
        adapter = get_chain_adapter("stellar")
        assert isinstance(adapter, StellarAdapter)


class TestStellarRouting:
    def test_stellar_is_cheapest(self):
        assert cheapest_chain() == "stellar"

    def test_is_stellar_address(self):
        assert is_stellar_address(STELLAR_G_ADDR)
        assert is_stellar_address(STELLAR_C_ADDR)
        assert not is_stellar_address("0x5aFE000000000000000000000000000000Ba53")
        assert not is_stellar_address("short")

    def test_stellar_address_routes_to_stellar(self):
        chain, fee = select_route(
            preferred_chain=None,
            auto_select_cheapest=True,
            payee_address=STELLAR_G_ADDR,
        )
        assert chain == "stellar"
        assert fee == 0.00001

    def test_emea_country_prefers_stellar(self):
        chain, fee = select_route(
            preferred_chain=None,
            auto_select_cheapest=True,
            payee_address="DiegoSo1anaWa11et000000000000000000000000",
            country="NG",
        )
        assert chain == "stellar"

    def test_non_emea_country_no_stellar(self):
        chain, fee = select_route(
            preferred_chain=None,
            auto_select_cheapest=True,
            payee_address="0x5aFE000000000000000000000000000000Ba53",
            country="US",
        )
        assert chain != "stellar"

    def test_stellar_preferred_countries_coverage(self):
        assert "NG" in STELLAR_PREFERRED_COUNTRIES
        assert "KE" in STELLAR_PREFERRED_COUNTRIES
        assert "DE" in STELLAR_PREFERRED_COUNTRIES
        assert "AE" in STELLAR_PREFERRED_COUNTRIES
        assert len(STELLAR_PREFERRED_COUNTRIES) >= 40


class TestStellarAnchor:
    def test_quote_nigeria(self):
        quote = stellar_anchor.quote(amount_usd=5000, country="NG")
        assert quote.ok
        assert quote.data["rail"] == "NIBSS/NIP via Cowrie"
        assert quote.data["fee_usd"] == 15.0
        assert quote.data["eta"] == "instant"
        assert quote.data["receive_asset"] == "NGNC"

    def test_quote_germany_eurc(self):
        quote = stellar_anchor.quote(amount_usd=10000, country="DE")
        assert quote.ok
        assert quote.data["receive_asset"] == "EURC"
        assert "SEPA" in quote.data["rail"]

    def test_compare_vs_traditional(self):
        comparison = stellar_anchor.compare_vs_traditional(amount_usd=5000, country="NG")
        assert comparison["savings_usd"] > 0
        assert comparison["savings_pct"] > 50

    def test_supported_countries(self):
        countries = stellar_anchor.supported_countries()
        assert "NG" in countries
        assert "DE" in countries
        assert len(countries) >= 10


class TestSorobanPolicy:
    def test_within_limits(self):
        result = soroban_policy.check_transfer(
            amount_usd=1000,
            to_address=STELLAR_G_ADDR,
            max_autonomous_usd=25000,
            daily_spent_usd=0,
            max_daily_usd=150000,
        )
        assert result.allowed
        assert result.requires_additional_signers == 0

    def test_above_autonomous_limit(self):
        result = soroban_policy.check_transfer(
            amount_usd=30000,
            to_address=STELLAR_G_ADDR,
            max_autonomous_usd=25000,
            daily_spent_usd=0,
            max_daily_usd=150000,
        )
        assert result.allowed
        assert result.requires_additional_signers >= 1

    def test_daily_limit_exceeded(self):
        result = soroban_policy.check_transfer(
            amount_usd=50000,
            to_address=STELLAR_G_ADDR,
            max_autonomous_usd=25000,
            daily_spent_usd=120000,
            max_daily_usd=150000,
        )
        assert not result.allowed

    def test_yield_deployment_check(self):
        result = soroban_policy.check_yield_deployment(
            amount_usd=100000, venue="stellar_tbill_us"
        )
        assert result.allowed
        assert result.requires_additional_signers == 0

    def test_large_yield_deployment(self):
        result = soroban_policy.check_yield_deployment(
            amount_usd=1_000_000, venue="stellar_tbill_us"
        )
        assert result.allowed
        assert result.requires_additional_signers == 2

    def test_contract_state(self):
        state = soroban_policy.get_contract_state()
        assert "policy_contract" in state
        assert state["policy_contract"]["status"] == "active"


class TestStellarRWA:
    def test_list_stellar_rwa_venues(self):
        venues = yield_adapter.list_stellar_rwa()
        assert len(venues) >= 4
        for v in venues:
            assert v["chain"] == "stellar"
            assert "rwa_metadata" in v

    def test_best_stellar_venue(self):
        venue = yield_adapter.best_stellar_venue("USDC")
        assert venue is not None
        assert venue["chain"] == "stellar"
        assert venue["apy"] > 0

    def test_rwa_metadata_contains_regulatory(self):
        venues = yield_adapter.list_stellar_rwa()
        for v in venues:
            assert "regulatory" in v["rwa_metadata"]
            assert "MiCA" in v["rwa_metadata"]["regulatory"] or "SEC" in v["rwa_metadata"]["regulatory"]

    def test_rwa_metadata_contains_soroban_contract(self):
        venues = yield_adapter.list_stellar_rwa()
        for v in venues:
            assert "soroban_contract" in v["rwa_metadata"]
            assert v["rwa_metadata"]["soroban_contract"].startswith("C")
