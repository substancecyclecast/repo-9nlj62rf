"""Payroll pipeline: parse -> plan -> propose -> execute, with compliance/routing."""

from __future__ import annotations

import pathlib

from app.services import ledger_service, payroll_service

SAMPLE = pathlib.Path(__file__).resolve().parents[1] / "data" / "sample_payroll.csv"


def test_parse_sample_csv():
    rows = payroll_service.parse_csv(SAMPLE.read_text())
    assert len(rows) == 15
    assert all(r["amount_usd"] > 0 for r in rows)
    assert any(r["prefers_fiat"] for r in rows)


def test_full_payroll_flow_keeps_books_balanced(db, org):
    rows = payroll_service.parse_csv(SAMPLE.read_text())
    batch = payroll_service.build_plan(db, organization_id=org.id, name="June", rows=rows)
    assert batch.payment_count == 15
    assert batch.total_usd > 0

    proposal = payroll_service.propose_batch(db, batch_id=batch.id)
    assert proposal["proposals"]
    # Multiple settlement chains should be used (base, solana, stellar, off-ramp, etc.).
    chains = {p["chain"] for p in proposal["proposals"]}
    assert len(chains) >= 3
    assert "stellar" in chains

    result = payroll_service.execute_batch(db, batch_id=batch.id)
    assert result["executed_payments"] == batch.payment_count

    tb = ledger_service.trial_balance(db, org.id)
    assert round(sum(r["debit"] for r in tb), 2) == round(sum(r["credit"] for r in tb), 2)


def test_cheapest_chain_routing_prefers_low_cost():
    # routing is exercised via build_plan; assert it picks a cheap EVM chain
    from app.services.routing import select_route

    chain, fee = select_route(
        preferred_chain=None, auto_select_cheapest=True,
        payee_address="0x1111111111111111111111111111111111111111",
    )
    assert chain in {"polygon", "base"}
    assert fee < 0.1


def test_compliance_blocks_restricted_country(db, org):
    rows = [
        {"name": "Blocked Payee", "amount_usd": 5000, "email": "", "country": "KP", "role": "",
         "chain": "base", "asset": "USDC", "wallet_address": "0x2222222222222222222222222222222222222222",
         "prefers_fiat": False, "memo": ""},
        {"name": "Good Payee", "amount_usd": 5000, "email": "", "country": "US", "role": "",
         "chain": "base", "asset": "USDC", "wallet_address": "0x3333333333333333333333333333333333333333",
         "prefers_fiat": False, "memo": ""},
    ]
    batch = payroll_service.build_plan(db, organization_id=org.id, name="screen", rows=rows)
    statuses = {p.payee_name: p.status for p in batch.payments}
    assert statuses["Blocked Payee"] == "blocked_compliance"
    assert statuses["Good Payee"] == "planned"
    # Only the cleared payee counts toward payable total.
    assert batch.total_usd == 5000
