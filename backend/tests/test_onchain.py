"""On-chain integration tests for Stellar testnet.

These tests make REAL transactions on Stellar testnet. They are gated behind
the ``onchain`` pytest marker and require:

    MANDATE_STELLAR_SIGNING_KEY — a funded testnet account secret key

Run with:
    PYTHONPATH=. pytest -m onchain -v

They are NOT run in the default CI pipeline to avoid flakiness from network
issues. A separate ``onchain`` CI job runs them with testnet secrets.
"""

from __future__ import annotations

import os

import pytest

onchain = pytest.mark.onchain

SKIP_REASON = "MANDATE_STELLAR_SIGNING_KEY not set — skipping on-chain tests"
HAS_KEY = bool(os.environ.get("MANDATE_STELLAR_SIGNING_KEY"))


@onchain
@pytest.mark.skipif(not HAS_KEY, reason=SKIP_REASON)
class TestStellarTestnetPayment:
    """Real payment on Stellar testnet."""

    def test_real_payment(self):
        """Submit a real XLM payment on testnet and verify via Horizon."""
        from stellar_sdk import Keypair, Network, Server, TransactionBuilder, Asset

        signing_key = os.environ["MANDATE_STELLAR_SIGNING_KEY"]
        source_kp = Keypair.from_secret(signing_key)
        server = Server("https://horizon-testnet.stellar.org")

        source_account = server.load_account(source_kp.public_key)

        # Send a small XLM payment to self (round-trip test)
        tx = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100,
            )
            .append_payment_op(
                destination=source_kp.public_key,
                asset=Asset.native(),
                amount="0.001",
            )
            .add_text_memo("mandate-onchain-test")
            .set_timeout(60)
            .build()
        )
        tx.sign(source_kp)
        resp = server.submit_transaction(tx)

        assert resp["successful"] is True
        tx_hash = resp["hash"]
        print(f"\n  Testnet tx: https://stellar.expert/explorer/testnet/tx/{tx_hash}")
        assert len(tx_hash) == 64

    def test_real_path_payment_strict_send(self):
        """Verify path_payment_strict_send builds correctly (dry-run)."""
        from stellar_sdk import Keypair, Network, Server, TransactionBuilder, Asset

        signing_key = os.environ["MANDATE_STELLAR_SIGNING_KEY"]
        source_kp = Keypair.from_secret(signing_key)
        server = Server("https://horizon-testnet.stellar.org")
        source_account = server.load_account(source_kp.public_key)

        # Build a path payment (XLM→XLM for simplicity, just to verify structure)
        tx = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100,
            )
            .append_path_payment_strict_send_op(
                destination=source_kp.public_key,
                send_asset=Asset.native(),
                send_amount="0.001",
                dest_asset=Asset.native(),
                dest_min="0.001",
                path=[],
            )
            .set_timeout(60)
            .build()
        )
        tx.sign(source_kp)
        resp = server.submit_transaction(tx)

        assert resp["successful"] is True
        tx_hash = resp["hash"]
        print(f"\n  Path payment tx: https://stellar.expert/explorer/testnet/tx/{tx_hash}")


@onchain
@pytest.mark.skipif(not HAS_KEY, reason=SKIP_REASON)
class TestStellarAdapterLive:
    """Test the StellarAdapter in live mode against testnet."""

    def test_live_build_transfer(self):
        """StellarAdapter._live_build_transfer submits a real tx."""
        from app.adapters.chains import StellarAdapter
        from stellar_sdk import Keypair

        os.environ["MANDATE_INTEGRATION_MODE"] = "live"
        os.environ["MANDATE_STELLAR_NETWORK"] = "testnet"

        adapter = StellarAdapter(mode="live")
        signing_key = os.environ["MANDATE_STELLAR_SIGNING_KEY"]
        source_kp = Keypair.from_secret(signing_key)

        result = adapter._live_build_transfer(
            account=source_kp.public_key,
            to=source_kp.public_key,  # self-payment for test
            asset="XLM",
            amount=0.001,
            sequence=0,
            memo="adapter-test",
        )

        assert result.get("live") is True
        assert result.get("tx_hash"), f"Expected tx_hash, got: {result}"
        if result.get("explorer_url"):
            print(f"\n  Adapter tx: {result['explorer_url']}")
