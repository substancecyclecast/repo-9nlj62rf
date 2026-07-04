"""Treasury aggregation and policy analysis.

Computes net asset value (NAV) across wallets and chains, stablecoin allocation,
idle-capital detection, and rebalancing/yield recommendations driven by the
organization's :class:`TreasuryPolicy`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.pricing import pricing
from app.adapters.yield_venues import yield_adapter
from app.core.constants import Stablecoin
from app.models import Organization, Wallet, YieldPosition

_STABLES = {s.value for s in Stablecoin}


def wallet_balances(db: Session, organization_id: int) -> list[dict]:
    wallets = db.scalars(
        select(Wallet).where(Wallet.organization_id == organization_id)
    ).all()
    out = []
    for w in wallets:
        assets = []
        for b in w.balances:
            b.usd_price = pricing.price_usd(b.asset)
            assets.append(
                {
                    "asset": b.asset,
                    "amount": round(b.amount, 6),
                    "usd_price": b.usd_price,
                    "usd_value": b.usd_value,
                }
            )
        out.append(
            {
                "wallet_id": w.id,
                "label": w.label,
                "chain": w.chain,
                "address": w.address,
                "kind": w.kind,
                "threshold": w.threshold,
                "owners": w.owners,
                "assets": sorted(assets, key=lambda a: a["usd_value"], reverse=True),
                "usd_value": round(sum(a["usd_value"] for a in assets), 2),
            }
        )
    return out


def yield_positions(db: Session, organization_id: int) -> list[dict]:
    positions = db.scalars(
        select(YieldPosition).where(
            YieldPosition.organization_id == organization_id,
            YieldPosition.status == "active",
        )
    ).all()
    return [
        {
            "id": p.id,
            "venue": p.venue,
            "chain": p.chain,
            "asset": p.asset,
            "principal_usd": round(p.principal_usd, 2),
            "apy": p.apy,
            "accrued_yield_usd": round(p.accrued_yield_usd, 2),
            "projected_annual_usd": yield_adapter.project_annual_income(p.principal_usd, p.apy),
        }
        for p in positions
    ]


def overview(db: Session, organization_id: int) -> dict:
    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("Organization not found")
    policy = org.policy

    wallets = wallet_balances(db, organization_id)
    positions = yield_positions(db, organization_id)

    liquid_usd = round(sum(w["usd_value"] for w in wallets), 2)
    yield_usd = round(sum(p["principal_usd"] + p["accrued_yield_usd"] for p in positions), 2)
    nav = round(liquid_usd + yield_usd, 2)

    stable_usd = 0.0
    volatile_usd = 0.0
    by_chain: dict[str, float] = {}
    by_asset: dict[str, float] = {}
    for w in wallets:
        by_chain[w["chain"]] = round(by_chain.get(w["chain"], 0.0) + w["usd_value"], 2)
        for a in w["assets"]:
            by_asset[a["asset"]] = round(by_asset.get(a["asset"], 0.0) + a["usd_value"], 2)
            if a["asset"] in _STABLES:
                stable_usd += a["usd_value"]
            else:
                volatile_usd += a["usd_value"]

    stable_pct = round(stable_usd / liquid_usd, 4) if liquid_usd else 0.0
    projected_yield = round(sum(p["projected_annual_usd"] for p in positions), 2)

    return {
        "organization": {"id": org.id, "name": org.name, "slug": org.slug},
        "nav_usd": nav,
        "liquid_usd": liquid_usd,
        "yield_usd": yield_usd,
        "stablecoin_usd": round(stable_usd, 2),
        "volatile_usd": round(volatile_usd, 2),
        "stablecoin_pct": stable_pct,
        "by_chain": by_chain,
        "by_asset": by_asset,
        "projected_annual_yield_usd": projected_yield,
        "policy": {
            "min_operating_reserve_usd": policy.min_operating_reserve_usd,
            "target_stablecoin_pct": policy.target_stablecoin_pct,
            "idle_yield_threshold_usd": policy.idle_yield_threshold_usd,
            "max_autonomous_transfer_usd": policy.max_autonomous_transfer_usd,
            "preferred_chain": policy.preferred_chain,
        },
        "wallet_count": len(wallets),
    }


def policy_recommendations(db: Session, organization_id: int) -> list[dict]:
    """Surface concrete actions: deploy idle cash, rebalance to stables, etc."""
    ov = overview(db, organization_id)
    org = db.get(Organization, organization_id)
    policy = org.policy
    recs: list[dict] = []

    # 1) Idle stablecoins above reserve should earn yield.
    deployable = ov["stablecoin_usd"] - policy.min_operating_reserve_usd
    if deployable >= policy.idle_yield_threshold_usd:
        venue = yield_adapter.best_venue(org.base_stablecoin)
        if venue:
            recs.append(
                {
                    "kind": "deploy_yield",
                    "severity": "opportunity",
                    "title": f"Deploy ${deployable:,.0f} idle {org.base_stablecoin} to {venue['venue']}",
                    "detail": (
                        f"{deployable:,.0f} {org.base_stablecoin} sits idle above the "
                        f"${policy.min_operating_reserve_usd:,.0f} reserve. {venue['venue']} "
                        f"yields {venue['apy'] * 100:.2f}% APY (~"
                        f"${deployable * venue['apy']:,.0f}/yr)."
                    ),
                    "amount_usd": round(deployable, 2),
                    "venue": venue["venue"],
                    "apy": venue["apy"],
                }
            )

    # 2) Volatile exposure beyond the stablecoin target should be de-risked.
    target = policy.target_stablecoin_pct
    if ov["liquid_usd"] and ov["stablecoin_pct"] < target - 0.02:
        gap_usd = round((target - ov["stablecoin_pct"]) * ov["liquid_usd"], 2)
        recs.append(
            {
                "kind": "rebalance_to_stable",
                "severity": "risk",
                "title": f"Convert ~${gap_usd:,.0f} volatile assets to {org.base_stablecoin}",
                "detail": (
                    f"Stablecoin allocation is {ov['stablecoin_pct'] * 100:.1f}% vs target "
                    f"{target * 100:.0f}%. Swap volatile holdings to reduce treasury risk."
                ),
                "amount_usd": gap_usd,
            }
        )

    # 3) Operating reserve breach.
    if ov["stablecoin_usd"] < policy.min_operating_reserve_usd:
        recs.append(
            {
                "kind": "reserve_breach",
                "severity": "critical",
                "title": "Operating reserve below policy minimum",
                "detail": (
                    f"Liquid stablecoins ${ov['stablecoin_usd']:,.0f} are below the "
                    f"${policy.min_operating_reserve_usd:,.0f} minimum. Withdraw from yield "
                    f"or pause discretionary spend."
                ),
                "amount_usd": round(policy.min_operating_reserve_usd - ov["stablecoin_usd"], 2),
            }
        )

    return recs
