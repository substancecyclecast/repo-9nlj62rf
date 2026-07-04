"""The autonomous CFO agent core.

Given a natural-language goal, the agent produces a plan of tool calls, executes
them in order, and records every step to the database as an auditable trace.

Two planning backends:

* ``deterministic`` (default, key-free): an intent parser maps the goal to a
  sequence of typed tool calls. This makes the whole product fully functional
  with no LLM credentials and keeps demos/tests reproducible.
* ``anthropic`` / ``openai``: if a key is configured, the same tools are exposed
  to the model for genuine multi-step tool-use. The deterministic planner is the
  fallback, so behaviour degrades gracefully.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.agent.tools import TOOLS, ToolContext, ToolResult
from app.core.config import settings
from app.models import AgentRun, AgentRunStep


@dataclass
class PlannedCall:
    tool: str
    arguments: dict = field(default_factory=dict)
    thought: str = ""


_AMOUNT_RE = re.compile(r"\$?\s*([\d][\d,]*\.?\d*)\s*(k|m)?", re.IGNORECASE)


def _parse_amount(text: str) -> float | None:
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    val = float(m.group(1).replace(",", ""))
    suffix = (m.group(2) or "").lower()
    if suffix == "k":
        val *= 1_000
    elif suffix == "m":
        val *= 1_000_000
    return round(val, 2)


class AgentCore:
    def __init__(self, db: Session, organization_id: int) -> None:
        self.db = db
        self.organization_id = organization_id
        self.ctx = ToolContext(db=db, organization_id=organization_id)

    # --- Public API -------------------------------------------------------

    def run(self, goal: str, *, structured_calls: list[dict] | None = None) -> AgentRun:
        run = AgentRun(
            organization_id=self.organization_id,
            goal=goal,
            status="running",
            provider=settings.llm_provider,
        )
        self.db.add(run)
        self.db.flush()

        if structured_calls:
            plan = [
                PlannedCall(tool=c["tool"], arguments=c.get("arguments", {}), thought="explicit")
                for c in structured_calls
            ]
        else:
            plan = self.plan(goal)

        observations: list[str] = []
        idx = 0
        for call in plan:
            self._log_step(run, idx, "thought", message=call.thought or f"Call {call.tool}")
            idx += 1
            result = self._invoke(call)
            self._log_step(
                run,
                idx,
                "tool",
                tool=call.tool,
                arguments=call.arguments,
                observation=result.data,
                message=result.message,
            )
            idx += 1
            observations.append(f"- {call.tool}: {result.message}")

        run.status = "completed"
        run.summary = self._summarize(goal, observations)
        self.db.flush()
        return run

    # --- Planning ---------------------------------------------------------

    def plan(self, goal: str) -> list[PlannedCall]:
        if settings.llm_provider in {"anthropic", "openai"}:
            llm_plan = self._llm_plan(goal)
            if llm_plan is not None:
                return llm_plan
        return self._deterministic_plan(goal)

    def _deterministic_plan(self, goal: str) -> list[PlannedCall]:
        g = goal.lower()
        plan: list[PlannedCall] = []

        wants_overview = any(
            k in g for k in ("overview", "status", "how much", "nav", "balance", "treasury", "summary")
        )
        wants_yield = any(k in g for k in ("yield", "apy", "earn", "idle", "park", "invest", "deploy"))
        wants_swap = any(k in g for k in ("swap", "convert", "exchange", "rebalance"))
        wants_pay = any(k in g for k in ("pay", "payroll", "contractor", "vendor", "payout"))
        wants_categorize = any(k in g for k in ("categori", "bookkeep", "books", "reconcile"))
        wants_recommend = any(
            k in g for k in ("recommend", "optimi", "what should", "advice", "suggest")
        )

        if wants_overview or not goal.strip():
            plan.append(PlannedCall("get_treasury_overview", thought="Assess current treasury."))

        if wants_swap:
            amt = _parse_amount(goal) or 100_000.0
            plan.append(
                PlannedCall(
                    "swap_quote",
                    {"from_asset": "USDC", "to_asset": "USDT", "amount": amt},
                    thought="Quote rebalancing swap.",
                )
            )

        if wants_yield:
            plan.append(PlannedCall("list_yield_venues", {"asset": "USDC"}, thought="Survey yield."))
            if any(k in g for k in ("deploy", "park", "invest", "put")):
                amt = _parse_amount(goal)
                if amt:
                    plan.append(
                        PlannedCall(
                            "deploy_yield",
                            {"amount_usd": amt, "asset": "USDC"},
                            thought="Deploy idle stablecoins to best venue.",
                        )
                    )

        if wants_categorize:
            plan.append(
                PlannedCall("categorize_transactions", thought="Reconcile the books.")
            )

        if wants_pay:
            plan.append(
                PlannedCall(
                    "get_balance",
                    {"asset": "USDC"},
                    thought="Confirm payout liquidity before paying.",
                )
            )

        if wants_recommend or not plan:
            plan.append(PlannedCall("recommend_actions", thought="Derive policy actions."))

        return plan

    def _llm_plan(self, goal: str) -> list[PlannedCall] | None:
        """Best-effort LLM planning. Returns None to trigger deterministic fallback.

        Implemented defensively: any import/auth/parse failure falls back so the
        product never hard-depends on external model availability.
        """
        try:
            from app.agent.llm import plan_with_llm  # local import keeps deps optional

            calls = plan_with_llm(goal)
            if not calls:
                return None
            return [PlannedCall(tool=c["tool"], arguments=c.get("arguments", {})) for c in calls]
        except Exception:  # noqa: BLE001 — deliberate graceful degradation
            return None

    # --- Execution helpers ------------------------------------------------

    def _invoke(self, call: PlannedCall) -> ToolResult:
        fn = TOOLS.get(call.tool)
        if fn is None:
            return ToolResult(ok=False, data={}, message=f"Unknown tool: {call.tool}")
        try:
            return fn(self.ctx, **call.arguments)
        except Exception as exc:  # noqa: BLE001 — surface tool errors as observations
            return ToolResult(ok=False, data={"error": str(exc)}, message=f"Error: {exc}")

    def _log_step(
        self,
        run: AgentRun,
        idx: int,
        kind: str,
        *,
        tool: str = "",
        arguments: dict | None = None,
        observation: dict | None = None,
        message: str = "",
    ) -> None:
        self.db.add(
            AgentRunStep(
                run_id=run.id,
                idx=idx,
                kind=kind,
                tool=tool,
                arguments_json=json.dumps(arguments or {}, default=str),
                observation_json=json.dumps(observation or {}, default=str),
                message=message,
            )
        )
        self.db.flush()

    def _summarize(self, goal: str, observations: list[str]) -> str:
        header = f"Goal: {goal.strip() or 'Treasury review'}"
        body = "\n".join(observations) if observations else "No actions taken."
        return f"{header}\n{body}"
