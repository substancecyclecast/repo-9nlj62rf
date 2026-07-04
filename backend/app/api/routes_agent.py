"""Autonomous agent endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentCore
from app.agent.tools import TOOL_SPECS
from app.api.schemas import AgentRunRequest
from app.core.database import get_db
from app.models import AgentRun
from app.services import audit_service, webhooks

router = APIRouter(tags=["agent"])


def _serialize_run(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "goal": run.goal,
        "status": run.status,
        "provider": run.provider,
        "summary": run.summary,
        "created_at": run.created_at.isoformat(),
        "steps": [
            {
                "idx": s.idx,
                "kind": s.kind,
                "tool": s.tool,
                "message": s.message,
                "arguments": json.loads(s.arguments_json or "{}"),
                "observation": json.loads(s.observation_json or "{}"),
            }
            for s in run.steps
        ],
    }


@router.get("/agent/tools")
def list_tools() -> list[dict]:
    return TOOL_SPECS


@router.post("/orgs/{org_id}/agent/run")
def run_agent(org_id: int, body: AgentRunRequest, db: Session = Depends(get_db)) -> dict:
    agent = AgentCore(db, org_id)
    run = agent.run(body.goal, structured_calls=body.structured_calls)
    db.flush()
    audit_service.record(
        db,
        organization_id=org_id,
        actor="agent",
        action="agent.run",
        resource=f"run:{run.id}",
        detail={"goal": run.goal, "status": run.status, "steps": len(run.steps)},
    )
    webhooks.emit(
        db,
        event="agent.run",
        summary=run.summary or run.goal,
        organization_id=org_id,
        fields={"status": run.status, "provider": run.provider, "steps": len(run.steps)},
    )
    db.commit()
    db.refresh(run)
    return _serialize_run(run)


@router.get("/orgs/{org_id}/agent/runs")
def list_runs(org_id: int, db: Session = Depends(get_db)) -> list[dict]:
    runs = db.scalars(
        select(AgentRun)
        .where(AgentRun.organization_id == org_id)
        .order_by(AgentRun.created_at.desc())
    ).all()
    return [_serialize_run(r) for r in runs]


@router.get("/orgs/{org_id}/agent/runs/{run_id}")
def get_run(org_id: int, run_id: int, db: Session = Depends(get_db)) -> dict:
    run = db.get(AgentRun, run_id)
    if run is None or run.organization_id != org_id:
        return {"error": "not found"}
    return _serialize_run(run)


@router.post("/orgs/{org_id}/agent/tool")
def invoke_tool(org_id: int, body: dict, db: Session = Depends(get_db)) -> dict:
    """Invoke a single agent tool directly (used by the frontend Stellar page)."""
    from app.agent.tools import TOOLS, ToolContext

    tool_name = body.get("tool", "")
    arguments = body.get("arguments", {})
    fn = TOOLS.get(tool_name)
    if fn is None:
        return {"ok": False, "data": {}, "message": f"Unknown tool: {tool_name}"}
    ctx = ToolContext(db=db, organization_id=org_id)
    result = fn(ctx, **arguments)
    db.commit()
    return {"ok": result.ok, "data": result.data, "message": result.message}
