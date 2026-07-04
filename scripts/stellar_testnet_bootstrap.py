#!/usr/bin/env python3
"""Mandate — Stellar Testnet Bootstrap Script.

Sets up the testnet environment for real Stellar transactions:
1. Creates and funds accounts via Friendbot
2. Issues test assets (USDC, EURC, NGNC) from an issuer account
3. Sets up trustlines from the treasury account
4. Creates DEX offers for path payment liquidity
5. Runs a demo payment and prints the explorer link

Usage:
    python scripts/stellar_testnet_bootstrap.py

Environment:
    MANDATE_STELLAR_SIGNING_KEY  — if set, uses this key as the treasury account;
                                    otherwise generates a new keypair.
"""

from __future__ import annotations

import sys
import time

import requests
from stellar_sdk import (
    Asset,
    Keypair,
    Network,
    Server,
    TransactionBuilder,
)

HORIZON = "https://horizon-testnet.stellar.org"
FRIENDBOT = "https://friendbot.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

server = Server(horizon_url=HORIZON)


def fund_account(public_key: str) -> None:
    """Fund an account via Stellar testnet Friendbot."""
    print(f"  Funding {public_key[:12]}...{public_key[-6:]} via Friendbot")
    resp = requests.get(FRIENDBOT, params={"addr": public_key}, timeout=30)
    if resp.status_code == 200:
        print("    Funded successfully")
    else:
        body = resp.text[:200]
        if "createAccountAlreadyExist" in body or "already exists" in body.lower():
            print("    Account already exists (OK)")
        else:
            print(f"    Warning: Friendbot returned {resp.status_code}: {body}")


def create_trustline(keypair: Keypair, asset: Asset) -> str:
    """Create a trustline from the given account to the asset."""
    account = server.load_account(keypair.public_key)
    tx = (
        TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100,
        )
        .append_change_trust_op(asset=asset)
        .set_timeout(300)
        .build()
    )
    tx.sign(keypair)
    resp = server.submit_transaction(tx)
    return resp["hash"]


def issue_asset(issuer_keypair: Keypair, dest_public: str, asset: Asset, amount: str) -> str:
    """Send issued asset from issuer to destination."""
    account = server.load_account(issuer_keypair.public_key)
    tx = (
        TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100,
        )
        .append_payment_op(destination=dest_public, asset=asset, amount=amount)
        .set_timeout(300)
        .build()
    )
    tx.sign(issuer_keypair)
    resp = server.submit_transaction(tx)
    return resp["hash"]


def create_sell_offer(keypair: Keypair, selling: Asset, buying: Asset, amount: str, price: str) -> str:
    """Create a DEX sell offer for path payment liquidity."""
    account = server.load_account(keypair.public_key)
    tx = (
        TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100,
        )
        .append_manage_sell_offer_op(
            selling=selling,
            buying=buying,
            amount=amount,
            price=price,
        )
        .set_timeout(300)
        .build()
    )
    tx.sign(keypair)
    resp = server.submit_transaction(tx)
    return resp["hash"]


def demo_payment(source_keypair: Keypair, dest_public: str, asset: Asset, amount: str, memo: str) -> dict:
    """Execute a demo payment and return transaction details."""
    account = server.load_account(source_keypair.public_key)
    tx = (
        TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100,
        )
        .append_payment_op(destination=dest_public, asset=asset, amount=amount)
        .add_text_memo(memo[:28])
        .set_timeout(300)
        .build()
    )
    tx.sign(source_keypair)
    resp = server.submit_transaction(tx)
    return resp


def main() -> None:
    import os

    print("=" * 60)
    print("Mandate — Stellar Testnet Bootstrap")
    print("=" * 60)
    print()

    # Step 1: Create accounts
    print("[1/6] Creating accounts...")

    signing_key = os.environ.get("MANDATE_STELLAR_SIGNING_KEY", "")
    if signing_key:
        treasury_kp = Keypair.from_secret(signing_key)
        print(f"  Using provided treasury key: {treasury_kp.public_key}")
    else:
        treasury_kp = Keypair.random()
        print(f"  Generated treasury keypair:")
        print(f"    Public:  {treasury_kp.public_key}")
        print(f"    Secret:  {treasury_kp.secret}")

    issuer_kp = Keypair.random()
    payee_kp = Keypair.random()

    print(f"  Issuer:    {issuer_kp.public_key}")
    print(f"  Payee:     {payee_kp.public_key}")
    print()

    # Step 2: Fund accounts via Friendbot
    print("[2/6] Funding accounts via Friendbot...")
    fund_account(treasury_kp.public_key)
    fund_account(issuer_kp.public_key)
    fund_account(payee_kp.public_key)
    time.sleep(2)
    print()

    # Step 3: Create test assets
    print("[3/6] Creating test assets...")
    usdc = Asset("USDC", issuer_kp.public_key)
    eurc = Asset("EURC", issuer_kp.public_key)
    ngnc = Asset("NGNC", issuer_kp.public_key)

    print(f"  USDC issuer: {issuer_kp.public_key}")
    print(f"  EURC issuer: {issuer_kp.public_key}")
    print(f"  NGNC issuer: {issuer_kp.public_key}")
    print()

    # Step 4: Set up trustlines
    print("[4/6] Setting up trustlines...")
    for asset in [usdc, eurc, ngnc]:
        tx_hash = create_trustline(treasury_kp, asset)
        print(f"  Treasury trustline for {asset.code}: {tx_hash[:16]}...")

    for asset in [usdc, eurc, ngnc]:
        tx_hash = create_trustline(payee_kp, asset)
        print(f"  Payee trustline for {asset.code}: {tx_hash[:16]}...")
    print()

    # Step 5: Issue test assets and create DEX liquidity
    print("[5/6] Issuing assets and creating DEX liquidity...")
    issue_asset(issuer_kp, treasury_kp.public_key, usdc, "1000000")
    print("  Issued 1,000,000 USDC to treasury")
    issue_asset(issuer_kp, treasury_kp.public_key, eurc, "500000")
    print("  Issued 500,000 EURC to treasury")
    issue_asset(issuer_kp, treasury_kp.public_key, ngnc, "100000000")
    print("  Issued 100,000,000 NGNC to treasury")

    # Create offers for path payment liquidity (USDC/EURC, USDC/NGNC)
    create_sell_offer(treasury_kp, eurc, usdc, "10000", "1.08")  # 1 EURC = 1.08 USDC
    print("  DEX offer: 10,000 EURC selling for USDC @ 1.08")
    create_sell_offer(treasury_kp, ngnc, usdc, "10000000", "0.00065")  # 1 NGNC ≈ $0.00065
    print("  DEX offer: 10,000,000 NGNC selling for USDC @ 0.00065")
    print()

    # Step 6: Demo payment
    print("[6/6] Running demo payment...")
    resp = demo_payment(
        treasury_kp,
        payee_kp.public_key,
        usdc,
        "5000",
        "Mandate payroll demo",
    )
    tx_hash = resp["hash"]
    ledger = resp.get("ledger", "?")
    explorer_url = f"https://stellar.expert/explorer/testnet/tx/{tx_hash}"

    print()
    print("=" * 60)
    print("BOOTSTRAP COMPLETE")
    print("=" * 60)
    print()
    print(f"Treasury account:  {treasury_kp.public_key}")
    print(f"Treasury secret:   {treasury_kp.secret}")
    print(f"Issuer account:    {issuer_kp.public_key}")
    print(f"Payee account:     {payee_kp.public_key}")
    print()
    print(f"Demo payment tx:   {tx_hash}")
    print(f"Ledger:            {ledger}")
    print(f"Explorer:          {explorer_url}")
    print()
    print("Set these environment variables to use live mode:")
    print(f"  export MANDATE_STELLAR_SIGNING_KEY={treasury_kp.secret}")
    print("  export MANDATE_INTEGRATION_MODE=live")
    print("  export MANDATE_STELLAR_NETWORK=testnet")


if __name__ == "__main__":
    main()
