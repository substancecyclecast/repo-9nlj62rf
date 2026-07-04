"""Agent tool implementations.

Each tool is a thin, well-typed wrapper around a service or adapter. The agent
core only ever acts through these tools, which gives us a complete, replayable
audit trail and lets us enforce the treasury policy at the tool boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.soroban_policy import soroban_policy
from app.adapters.stellar_anchor import stellar_anchor
from app.adapters.swap import swap
from app.adapters.yield_venues import yield_adapter
from app.core.constants import TxStatus, TxType
from app.models import Organization, Transaction, YieldPosition
from app.services import ledger_service, payroll_service, treasury_service
from app.services.categorization import categorize


@dataclass
class ToolResult:
    ok: bool
    data: dict
    message: str


@dataclass
class ToolContext:
    db: Session
    organization_id: int


# --- Tool implementations -------------------------------------------------


def get_treasury_overview(ctx: ToolContext, **_: Any) -> ToolResult:
    ov = treasury_service.overview(ctx.db, ctx.organization_id)
    return ToolResult(
        ok=True,
        data=ov,
        message=(
            f"NAV ${ov['nav_usd']:,.0f} "
            f"(liquid ${ov['liquid_usd']:,.0f}, yield ${ov['yield_usd']:,.0f}); "
            f"{ov['stablecoin_pct'] * 100:.1f}% in stablecoins across "
            f"{ov['wallet_count']} wallets."
        ),
    )


def get_balance(ctx: ToolContext, *, asset: str | None = None, **_: Any) -> ToolResult:
    wallets = treasury_service.wallet_balances(ctx.db, ctx.organization_id)
    if asset:
        asset = asset.upper()
        total = round(
            sum(a["usd_value"] for w in wallets for a in w["assets"] if a["asset"] == asset), 2
        )
        return ToolResult(
            ok=True,
            data={"asset": asset, "usd_value": total},
            message=f"{asset} balance: ${total:,.2f}",
        )
    return ToolResult(
        ok=True,
        data={"wallets": wallets},
        message=f"{len(wallets)} wallets aggregated.",
    )


def recommend_actions(ctx: ToolContext, **_: Any) -> ToolResult:
    recs = treasury_service.policy_recommendations(ctx.db, ctx.organization_id)
    return ToolResult(
        ok=True,
        data={"recommendations": recs},
        message=f"{len(recs)} policy-driven recommendation(s).",
    )


def list_yield_venues(ctx: ToolContext, *, asset: str = "USDC", **_: Any) -> ToolResult:
    venues = yield_adapter.list_venues(asset)
    return ToolResult(
        ok=True, data={"venues": venues}, message=f"{len(venues)} venues for {asset}."
    )


def swap_quote(
    ctx: ToolContext,
    *,
    from_asset: str,
    to_asset: str,
    amount: float,
    from_chain: str = "base",
    to_chain: str = "base",
    **_: Any,
) -> ToolResult:
    q = swap.quote(
        from_asset=from_asset,
        to_asset=to_asset,
        amount=float(amount),
        from_chain=from_chain,
        to_chain=to_chain,
    )
    return ToolResult(ok=q.ok, data=q.data, message=q.detail)


def propose_transfer(
    ctx: ToolContext,
    *,
    to_address: str,
    amount_usd: float,
    asset: str = "USDC",
    chain: str = "base",
    counterparty: str = "",
    memo: str = "",
    category: str = "vendor",
    **_: Any,
) -> ToolResult:
    """Create a single transfer. Honors the policy autonomy limit: amounts at or
    below the limit can be auto-signed; larger ones require human signatures."""
    org = ctx.db.get(Organization, ctx.organization_id)
    policy = org.policy
    amount_usd = float(amount_usd)
    requires_human = amount_usd > policy.max_autonomous_transfer_usd
    status = TxStatus.AWAITING_SIGNATURES if requires_human else TxStatus.PROPOSED

    tx = Transaction(
        organization_id=ctx.organization_id,
        tx_type=TxType.VENDOR,
        status=status,
        chain=chain,
        asset=asset,
        amount=amount_usd,
        usd_value=amount_usd,
        counterparty=counterparty,
        to_address=to_address,
        memo=memo,
        category=category,
        created_by="agent",
    )
    ctx.db.add(tx)
    ctx.db.flush()
    return ToolResult(
        ok=True,
        data={
            "transaction_id": tx.id,
            "status": tx.status,
            "requires_human_signatures": requires_human,
            "policy_limit_usd": policy.max_autonomous_transfer_usd,
        },
        message=(
            f"Proposed ${amount_usd:,.2f} {asset} to {counterparty or to_address} on {chain}. "
            + (
                "Above autonomy limit — awaiting human co-signers."
                if requires_human
                else "Within autonomy limit."
            )
        ),
    )


def batch_payout(
    ctx: ToolContext,
    *,
    name: str = "Agent payout",
    rows: list[dict] | None = None,
    csv_content: str | None = None,
    auto_execute: bool = False,
    **_: Any,
) -> ToolResult:
    """Plan (and optionally execute) a batch payout from rows or CSV content."""
    if csv_content:
        rows = payroll_service.parse_csv(csv_content)
    if not rows:
        return ToolResult(ok=False, data={}, message="No rows or csv_content provided.")

    batch = payroll_service.build_plan(
        ctx.db, organization_id=ctx.organization_id, name=name, rows=rows
    )
    proposal = payroll_service.propose_batch(ctx.db, batch_id=batch.id)
    result = {
        "batch_id": batch.id,
        "payment_count": batch.payment_count,
        "total_usd": batch.total_usd,
        "total_fees_usd": batch.total_fees_usd,
        "proposals": proposal["proposals"],
    }
    msg = (
        f"Planned batch '{name}': {batch.payment_count} payees, "
        f"${batch.total_usd:,.2f} + ${batch.total_fees_usd:,.2f} fees across "
        f"{len(proposal['proposals'])} chain(s)."
    )
    if auto_execute:
        execed = payroll_service.execute_batch(ctx.db, batch_id=batch.id)
        result["execution"] = execed
        msg += f" Executed {execed['executed_payments']} payments."
    return ToolResult(ok=True, data=result, message=msg)


def deploy_yield(
    ctx: ToolContext, *, amount_usd: float, asset: str = "USDC", venue: str | None = None, **_: Any
) -> ToolResult:
    """Move idle stablecoins into the best (or specified) yield venue."""
    chosen = (
        {"venue": venue, **(yield_adapter.list_venues(asset)[0])}
        if venue is None
        else next(
            (v for v in yield_adapter.list_venues(asset) if v["venue"] == venue),
            yield_adapter.best_venue(asset),
        )
    )
    if not chosen:
        return ToolResult(ok=False, data={}, message=f"No yield venue for {asset}.")
    amount_usd = float(amount_usd)
    pos = YieldPosition(
        organization_id=ctx.organization_id,
        venue=chosen["venue"],
        chain=chosen.get("chain", "base"),
        asset=asset,
        principal_usd=amount_usd,
        apy=chosen["apy"],
    )
    ctx.db.add(pos)
    # Double-entry: move cash from treasury (1000) to yield positions (1100).
    ledger_service.post_entry(
        ctx.db,
        organization_id=ctx.organization_id,
        lines=[("1100", amount_usd, 0.0), ("1000", 0.0, amount_usd)],
        memo=f"Deploy ${amount_usd:,.0f} {asset} to {chosen['venue']} @ {chosen['apy'] * 100:.2f}%",
        reference=f"yield:{chosen['venue']}",
    )
    ctx.db.flush()
    return ToolResult(
        ok=True,
        data={
            "position_id": pos.id,
            "venue": chosen["venue"],
            "apy": chosen["apy"],
            "projected_annual_usd": yield_adapter.project_annual_income(amount_usd, chosen["apy"]),
        },
        message=(
            f"Deployed ${amount_usd:,.0f} {asset} to {chosen['venue']} at "
            f"{chosen['apy'] * 100:.2f}% APY (~"
            f"${yield_adapter.project_annual_income(amount_usd, chosen['apy']):,.0f}/yr)."
        ),
    )


def categorize_transactions(ctx: ToolContext, **_: Any) -> ToolResult:
    """Auto-categorize any uncategorized transactions using rules + heuristics."""
    txs = ctx.db.scalars(
        select(Transaction).where(
            Transaction.organization_id == ctx.organization_id,
            Transaction.category == "uncategorized",
        )
    ).all()
    updated = 0
    for tx in txs:
        cat = categorize(counterparty=tx.counterparty, memo=tx.memo, tx_type=tx.tx_type)
        if cat:
            tx.category = cat
            updated += 1
    ctx.db.flush()
    return ToolResult(
        ok=True,
        data={"updated": updated, "scanned": len(txs)},
        message=f"Categorized {updated}/{len(txs)} uncategorized transactions.",
    )


def stellar_cross_border_quote(
    ctx: ToolContext, *, amount_usd: float, country: str, asset: str = "USDC", **_: Any
) -> ToolResult:
    """Quote a Stellar anchor cross-border payment (EMEA/Africa corridors)."""
    quote = stellar_anchor.quote(amount_usd=float(amount_usd), country=country, asset=asset)
    comparison = stellar_anchor.compare_vs_traditional(
        amount_usd=float(amount_usd), country=country
    )
    return ToolResult(
        ok=True,
        data={"quote": quote.data, "vs_traditional": comparison},
        message=(
            f"Stellar anchor: ${amount_usd:,.0f} to {country} via {quote.data['rail']} — "
            f"fee ${quote.data['fee_usd']:.2f} ({quote.data['eta']}). "
            f"Saves ${comparison['savings_usd']:.2f} vs traditional ({comparison['savings_pct']:.0f}% cheaper)."
        ),
    )


def deploy_rwa(
    ctx: ToolContext,
    *,
    amount_usd: float,
    asset: str = "USDC",
    venue: str = "stellar_tbill_us",
    **_: Any,
) -> ToolResult:
    """Deploy treasury funds into tokenized RWA (T-bills, bonds) on Stellar."""
    amount_usd = float(amount_usd)
    policy_check = soroban_policy.check_yield_deployment(
        amount_usd=amount_usd, venue=venue
    )
    chosen = next(
        (v for v in yield_adapter.list_venues(asset) if v["venue"] == venue),
        yield_adapter.best_stellar_venue(asset),
    )
    if not chosen:
        return ToolResult(ok=False, data={}, message=f"No Stellar RWA venue for {asset}.")

    pos = YieldPosition(
        organization_id=ctx.organization_id,
        venue=chosen["venue"],
        chain="stellar",
        asset=asset,
        principal_usd=amount_usd,
        apy=chosen["apy"],
    )
    ctx.db.add(pos)
    ledger_service.post_entry(
        ctx.db,
        organization_id=ctx.organization_id,
        lines=[("1300", amount_usd, 0.0), ("1000", 0.0, amount_usd)],
        memo=f"Deploy ${amount_usd:,.0f} {asset} to {chosen['venue']} (RWA on Stellar)",
        reference=f"rwa:{chosen['venue']}",
    )
    ctx.db.flush()
    return ToolResult(
        ok=True,
        data={
            "position_id": pos.id,
            "venue": chosen["venue"],
            "apy": chosen["apy"],
            "chain": "stellar",
            "policy_check": {
                "allowed": policy_check.allowed,
                "reason": policy_check.reason,
                "additional_signers": policy_check.requires_additional_signers,
            },
            "rwa_metadata": chosen.get("rwa_metadata"),
        },
        message=(
            f"Deployed ${amount_usd:,.0f} {asset} to {chosen['venue']} (Stellar RWA) at "
            f"{chosen['apy'] * 100:.2f}% APY. "
            f"Policy: {policy_check.reason}."
        ),
    )


def check_soroban_policy(
    ctx: ToolContext,
    *,
    amount_usd: float,
    to_address: str,
    **_: Any,
) -> ToolResult:
    """Check if a transfer passes the on-chain Soroban policy contract."""
    org = ctx.db.get(Organization, ctx.organization_id)
    policy = org.policy
    result = soroban_policy.check_transfer(
        amount_usd=float(amount_usd),
        to_address=to_address,
        max_autonomous_usd=policy.max_autonomous_transfer_usd,
        daily_spent_usd=0.0,
        max_daily_usd=policy.max_autonomous_daily_usd,
    )
    return ToolResult(
        ok=True,
        data={
            "allowed": result.allowed,
            "reason": result.reason,
            "contract_id": result.contract_id,
            "additional_signers_required": result.requires_additional_signers,
        },
        message=f"Soroban policy: {'ALLOWED' if result.allowed else 'BLOCKED'} — {result.reason}",
    )


def list_stellar_rwa_venues(ctx: ToolContext, **_: Any) -> ToolResult:
    """List available Stellar-native RWA yield products (tokenized T-bills, bonds)."""
    venues = yield_adapter.list_stellar_rwa()
    return ToolResult(
        ok=True,
        data={"venues": venues},
        message=f"{len(venues)} Stellar RWA venue(s) available.",
    )


# --- Registry -------------------------------------------------------------

ToolFn = Callable[..., ToolResult]

TOOLS: dict[str, ToolFn] = {
    "get_treasury_overview": get_treasury_overview,
    "get_balance": get_balance,
    "recommend_actions": recommend_actions,
    "list_yield_venues": list_yield_venues,
    "swap_quote": swap_quote,
    "propose_transfer": propose_transfer,
    "batch_payout": batch_payout,
    "deploy_yield": deploy_yield,
    "categorize_transactions": categorize_transactions,
    # Stellar-specific tools
    "stellar_cross_border_quote": stellar_cross_border_quote,
    "deploy_rwa": deploy_rwa,
    "check_soroban_policy": check_soroban_policy,
    "list_stellar_rwa_venues": list_stellar_rwa_venues,
}

# JSON-schema-ish specs exposed to an LLM for tool-use (and for the API docs).
TOOL_SPECS: list[dict] = [
    {
        "name": "get_treasury_overview",
        "description": "Aggregate NAV, allocation, and policy posture across all wallets/chains.",
        "parameters": {},
    },
    {
        "name": "get_balance",
        "description": "Get total USD balance, optionally filtered to one asset.",
        "parameters": {"asset": "string (optional)"},
    },
    {
        "name": "recommend_actions",
        "description": "Policy-driven recommendations (deploy idle cash, rebalance, reserve).",
        "parameters": {},
    },
    {
        "name": "list_yield_venues",
        "description": "List available yield venues and APYs for an asset.",
        "parameters": {"asset": "string (default USDC)"},
    },
    {
        "name": "swap_quote",
        "description": "Quote a stablecoin/asset swap or cross-chain bridge via Li.Fi.",
        "parameters": {
            "from_asset": "string",
            "to_asset": "string",
            "amount": "number",
            "from_chain": "string",
            "to_chain": "string",
        },
    },
    {
        "name": "propose_transfer",
        "description": "Propose a single multisig transfer; auto-signs within policy limit.",
        "parameters": {
            "to_address": "string",
            "amount_usd": "number",
            "asset": "string",
            "chain": "string",
            "counterparty": "string",
            "memo": "string",
            "category": "string",
        },
    },
    {
        "name": "batch_payout",
        "description": "Plan/execute a batch payout (payroll/vendors) from rows or CSV content.",
        "parameters": {
            "name": "string",
            "rows": "array of {name, amount_usd, country, chain, asset, wallet_address}",
            "csv_content": "string (optional)",
            "auto_execute": "boolean",
        },
    },
    {
        "name": "deploy_yield",
        "description": "Deploy idle stablecoins into a yield venue.",
        "parameters": {"amount_usd": "number", "asset": "string", "venue": "string (optional)"},
    },
    {
        "name": "categorize_transactions",
        "description": "Auto-categorize uncategorized transactions for the books.",
        "parameters": {},
    },
    {
        "name": "stellar_cross_border_quote",
        "description": "Quote a Stellar anchor cross-border payment for EMEA/Africa corridors. Compares vs traditional off-ramp.",
        "parameters": {"amount_usd": "number", "country": "string (ISO 2-letter)", "asset": "string"},
    },
    {
        "name": "deploy_rwa",
        "description": "Deploy treasury into tokenized RWA (T-bills, bonds) on Stellar via Soroban contracts.",
        "parameters": {"amount_usd": "number", "asset": "string", "venue": "string (optional)"},
    },
    {
        "name": "check_soroban_policy",
        "description": "Check if a transfer passes the on-chain Soroban policy contract on Stellar.",
        "parameters": {"amount_usd": "number", "to_address": "string"},
    },
    {
        "name": "list_stellar_rwa_venues",
        "description": "List Stellar-native RWA yield products (tokenized T-bills, EU bonds, money market funds).",
        "parameters": {},
    },
]
