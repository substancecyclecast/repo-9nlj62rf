"""Payroll & vendor payout service.

Pipeline: CSV/JSON import -> per-payee plan (compliance screen + cheapest-chain
routing + fiat off-ramp where required + fee estimate) -> grouped multisig
proposals (one Safe/Squads batch per chain) -> execution -> double-entry posting.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.chains import get_chain_adapter
from app.adapters.compliance import compliance
from app.adapters.offramp import offramp
from app.core.constants import TxStatus, TxType
from app.models import (
    Contractor,
    Organization,
    Payment,
    PayrollBatch,
    Transaction,
    Wallet,
)
from app.services import ledger_service
from app.services.routing import select_route

REQUIRED_COLUMNS = {"name", "amount_usd"}

_ROW_DEFAULTS = {
    "name": "",
    "email": "",
    "country": "",
    "role": "",
    "amount_usd": 0.0,
    "chain": "",
    "asset": "USDC",
    "wallet_address": "",
    "prefers_fiat": False,
    "memo": "",
}


def _normalize_row(row: dict) -> dict:
    """Fill missing keys so callers (API/agent) need only supply name + amount."""
    out = dict(_ROW_DEFAULTS)
    out.update({k: v for k, v in row.items() if v is not None})
    out["country"] = str(out["country"]).upper()
    out["asset"] = str(out["asset"] or "USDC").upper()
    out["chain"] = str(out["chain"]).lower()
    out["amount_usd"] = round(float(out["amount_usd"]), 2)
    return out


class PayrollError(ValueError):
    pass


def parse_csv(content: str) -> list[dict]:
    """Parse a payroll CSV into normalized rows.

    Recognized headers (case-insensitive): name, email, country, role,
    amount_usd (or amount), chain, asset, wallet_address (or address),
    prefers_fiat, memo.
    """
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        raise PayrollError("CSV has no header row")
    headers = {h.strip().lower(): h for h in reader.fieldnames}

    def col(row: dict, *names: str) -> str:
        for n in names:
            if n in headers and row.get(headers[n]) is not None:
                return str(row[headers[n]]).strip()
        return ""

    rows: list[dict] = []
    for i, raw in enumerate(reader, start=2):
        name = col(raw, "name", "payee", "contractor")
        amount_str = col(raw, "amount_usd", "amount", "usd")
        if not name and not amount_str:
            continue
        if not name:
            raise PayrollError(f"Row {i}: missing payee name")
        try:
            amount = round(float(amount_str.replace(",", "").replace("$", "")), 2)
        except ValueError as exc:
            raise PayrollError(f"Row {i}: invalid amount '{amount_str}'") from exc
        if amount <= 0:
            raise PayrollError(f"Row {i}: amount must be positive")
        prefers_fiat = col(raw, "prefers_fiat", "fiat").lower() in {"1", "true", "yes", "y"}
        rows.append(
            {
                "name": name,
                "email": col(raw, "email"),
                "country": col(raw, "country").upper(),
                "role": col(raw, "role", "title"),
                "amount_usd": amount,
                "chain": col(raw, "chain").lower(),
                "asset": (col(raw, "asset", "token") or "USDC").upper(),
                "wallet_address": col(raw, "wallet_address", "address", "wallet"),
                "prefers_fiat": prefers_fiat,
                "memo": col(raw, "memo", "note"),
            }
        )
    if not rows:
        raise PayrollError("No payable rows found in CSV")
    return rows


def build_plan(
    db: Session, *, organization_id: int, name: str, rows: list[dict]
) -> PayrollBatch:
    """Create a draft batch with a fully-routed, compliance-screened plan."""
    org = db.get(Organization, organization_id)
    if org is None:
        raise PayrollError("Organization not found")
    policy = org.policy

    batch = PayrollBatch(
        organization_id=organization_id, name=name, status="draft", currency="USD"
    )
    db.add(batch)
    db.flush()

    total = 0.0
    total_fees = 0.0
    for raw_row in rows:
        row = _normalize_row(raw_row)
        if not row["name"]:
            raise PayrollError("Payroll row missing payee name")
        contractor = _upsert_contractor(db, organization_id, row)
        screen = compliance.screen(
            name=row["name"], country=row["country"], wallet_address=row["wallet_address"]
        )

        if row["prefers_fiat"] or contractor.prefers_fiat:
            quote = offramp.quote(amount_usd=row["amount_usd"], country=row["country"])
            chain = "off-ramp"
            fee = quote.data["fee_usd"]
            route = f"off-ramp:{quote.data['rail']}"
        else:
            address = row["wallet_address"] or contractor.wallet_address
            preferred = row["chain"] or contractor.payout_chain or policy.preferred_chain
            chain, fee = select_route(
                preferred_chain=preferred,
                auto_select_cheapest=policy.auto_select_cheapest_chain,
                payee_address=address or "0x0000000000000000000000000000000000000000",
                country=row["country"],
            )
            route = "on-chain" if chain != "stellar" else "stellar-anchor"

        status = "planned" if screen["cleared"] else "blocked_compliance"
        payment = Payment(
            batch_id=batch.id,
            contractor_id=contractor.id,
            payee_name=row["name"],
            country=row["country"],
            amount_usd=row["amount_usd"],
            chain=chain,
            asset=row["asset"],
            to_address=row["wallet_address"] or contractor.wallet_address,
            fee_usd=fee,
            route=route,
            status=status,
            memo=row["memo"] or (screen["reason"] if not screen["cleared"] else ""),
        )
        db.add(payment)
        if screen["cleared"]:
            total += row["amount_usd"]
            total_fees += fee

    batch.total_usd = round(total, 2)
    batch.total_fees_usd = round(total_fees, 2)
    batch.payment_count = len(rows)
    db.flush()
    return batch


def _upsert_contractor(db: Session, organization_id: int, row: dict) -> Contractor:
    contractor = db.scalar(
        select(Contractor).where(
            Contractor.organization_id == organization_id,
            Contractor.name == row["name"],
        )
    )
    if contractor is None:
        contractor = Contractor(organization_id=organization_id, name=row["name"])
        db.add(contractor)
    contractor.email = row["email"] or contractor.email
    contractor.country = row["country"] or contractor.country
    contractor.role = row["role"] or contractor.role
    contractor.wallet_address = row["wallet_address"] or contractor.wallet_address
    contractor.payout_asset = row["asset"] or contractor.payout_asset
    if row["chain"]:
        contractor.payout_chain = row["chain"]
    contractor.prefers_fiat = row["prefers_fiat"] or contractor.prefers_fiat
    screen = compliance.screen(
        name=row["name"], country=row["country"], wallet_address=row["wallet_address"]
    )
    contractor.kyc_status = screen["status"]
    db.flush()
    return contractor


def propose_batch(db: Session, *, batch_id: int) -> dict:
    """Turn a draft batch into multisig proposals grouped by settlement chain."""
    batch = db.get(PayrollBatch, batch_id)
    if batch is None:
        raise PayrollError("Batch not found")
    payable = [p for p in batch.payments if p.status == "planned"]
    if not payable:
        raise PayrollError("No payable (compliance-cleared) payments in batch")

    org_id = batch.organization_id
    proposals: list[dict] = []
    by_chain: dict[str, list[Payment]] = {}
    for p in payable:
        by_chain.setdefault(p.chain, []).append(p)

    for chain, payments in by_chain.items():
        total = round(sum(p.amount_usd for p in payments), 2)
        if chain == "off-ramp":
            safe_tx_hash = f"bridge-batch-{batch.id}"
            proposal = {"type": "bridge_offramp_batch", "safe_tx_hash": safe_tx_hash}
        else:
            wallet = _funding_wallet(db, org_id, chain)
            adapter = get_chain_adapter(chain)
            if adapter.name == "squads":
                proposal = adapter.build_transfer(
                    multisig=wallet.address if wallet else "SQUADSxxxxMULTISIGxxxxPLACEHOLDER",
                    to=f"batch:{len(payments)}",
                    asset=payments[0].asset,
                    amount=total,
                    index=batch.id,
                )
            elif adapter.name == "stellar":
                proposal = adapter.build_transfer(
                    account=wallet.address if wallet else "GPLACEHOLDERSTELLARACCOUNT000000000000000000000000",
                    to=f"batch:{len(payments)}",
                    asset=payments[0].asset,
                    amount=total,
                    sequence=batch.id,
                    memo=f"payroll-batch-{batch.id}",
                )
            else:
                proposal = adapter.build_transfer(
                    chain=chain,
                    safe_address=wallet.address if wallet else "0xSAFE",
                    to=f"batch:{len(payments)}",
                    asset=payments[0].asset,
                    amount=total,
                    nonce=batch.id,
                )
            safe_tx_hash = proposal.get("safe_tx_hash") or proposal.get("tx_hash", "")

        for p in payments:
            tx = Transaction(
                organization_id=org_id,
                tx_type=TxType.PAYROLL,
                status=TxStatus.AWAITING_SIGNATURES,
                chain=p.chain,
                asset=p.asset,
                amount=p.amount_usd,
                usd_value=p.amount_usd,
                fee_usd=p.fee_usd,
                counterparty=p.payee_name,
                to_address=p.to_address,
                memo=f"Payroll batch '{batch.name}' — {p.payee_name}",
                category="payroll",
                safe_tx_hash=safe_tx_hash,
                created_by="agent",
                batch_id=batch.id,
            )
            db.add(tx)
            p.status = "proposed"

        proposals.append(
            {
                "chain": chain,
                "payment_count": len(payments),
                "total_usd": total,
                "safe_tx_hash": safe_tx_hash,
                "required_signatures": _threshold(db, org_id, chain),
                "proposal": proposal,
            }
        )

    batch.status = "proposed"
    db.flush()
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "proposals": proposals,
        "total_usd": batch.total_usd,
        "total_fees_usd": batch.total_fees_usd,
    }


def execute_batch(db: Session, *, batch_id: int) -> dict:
    """Mark proposals executed and post double-entry journal entries."""
    batch = db.get(PayrollBatch, batch_id)
    if batch is None:
        raise PayrollError("Batch not found")
    txs = db.scalars(
        select(Transaction).where(
            Transaction.batch_id == batch_id,
            Transaction.status == TxStatus.AWAITING_SIGNATURES,
        )
    ).all()
    if not txs:
        raise PayrollError("No awaiting-signature transactions; propose the batch first")

    executed = 0
    total_amount = 0.0
    total_fees = 0.0
    for tx in txs:
        adapter_chain = tx.chain if tx.chain != "off-ramp" else "base"
        try:
            adapter = get_chain_adapter(adapter_chain)
            result = adapter.execute(safe_tx_hash=tx.safe_tx_hash)
            tx.tx_hash = result["tx_hash"]
        except ValueError:
            tx.tx_hash = f"offramp-{tx.id}"
        tx.status = TxStatus.EXECUTED
        tx.signatures = _threshold(db, batch.organization_id, tx.chain)
        tx.executed_at = datetime.now(timezone.utc)
        executed += 1
        total_amount += tx.amount
        total_fees += tx.fee_usd

    # Double-entry: expense the payroll + fees, credit treasury cash.
    if total_amount or total_fees:
        gross = round(total_amount + total_fees, 2)
        entry = ledger_service.post_entry(
            db,
            organization_id=batch.organization_id,
            lines=[
                ("5000", round(total_amount, 2), 0.0),
                ("5200", round(total_fees, 2), 0.0),
                ("1000", 0.0, gross),
            ],
            memo=f"Payroll batch '{batch.name}' executed ({executed} payments)",
            reference=f"batch:{batch.id}",
            source="agent",
        )
        for tx in txs:
            tx.journal_entry_id = entry.id

    for p in batch.payments:
        if p.status == "proposed":
            p.status = "executed"
    batch.status = "executed"
    db.flush()
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "executed_payments": executed,
        "total_usd": round(total_amount, 2),
        "total_fees_usd": round(total_fees, 2),
    }


def _funding_wallet(db: Session, organization_id: int, chain: str) -> Wallet | None:
    return db.scalar(
        select(Wallet).where(
            Wallet.organization_id == organization_id, Wallet.chain == chain
        )
    )


def _threshold(db: Session, organization_id: int, chain: str) -> int:
    wallet = _funding_wallet(db, organization_id, chain)
    return wallet.threshold if wallet else 2
