"""Agent core planning + tool execution and reporting."""

from __future__ import annotations

from app.agent.orchestrator import AgentCore
from app.agent.tools import ToolContext, batch_payout
from app.reports import auditor_pdf
from app.services import treasury_service


def test_agent_overview_run(db, org):
    agent = AgentCore(db, org.id)
    run = agent.run("Give me a full treasury overview and recommendations")
    tools_used = [s.tool for s in run.steps if s.kind == "tool"]
    assert "get_treasury_overview" in tools_used
    assert "recommend_actions" in tools_used
    assert run.status == "completed"
    assert run.summary


def test_agent_deploy_yield_run(db, org):
    agent = AgentCore(db, org.id)
    run = agent.run("Deploy $200,000 idle USDC into the best yield venue")
    tools_used = [s.tool for s in run.steps if s.kind == "tool"]
    assert "deploy_yield" in tools_used
    positions = treasury_service.yield_positions(db, org.id)
    assert any(p["principal_usd"] == 200000 for p in positions)


def test_batch_payout_tool_executes(db, org):
    ctx = ToolContext(db=db, organization_id=org.id)
    rows = [
        {"name": "Alice", "amount_usd": 1000, "country": "US", "chain": "base", "asset": "USDC",
         "wallet_address": "0x4444444444444444444444444444444444444444"},
        {"name": "Bob", "amount_usd": 2000, "country": "DE", "chain": "", "asset": "USDC",
         "wallet_address": "0x5555555555555555555555555555555555555555"},
    ]
    result = batch_payout(ctx, name="t", rows=rows, auto_execute=True)
    assert result.ok
    assert result.data["execution"]["executed_payments"] == 2


def test_propose_transfer_respects_policy_limit(db, org):
    from app.agent.tools import propose_transfer

    ctx = ToolContext(db=db, organization_id=org.id)
    small = propose_transfer(ctx, to_address="0xabc", amount_usd=10_000, counterparty="X")
    big = propose_transfer(ctx, to_address="0xabc", amount_usd=500_000, counterparty="Y")
    assert small.data["requires_human_signatures"] is False
    assert big.data["requires_human_signatures"] is True


def test_auditor_pdf_generates(db, org):
    pdf = auditor_pdf.build_auditor_report(db, org.id)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000
