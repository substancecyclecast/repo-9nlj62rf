"""LangGraph StateGraph: Planner → Sourcer → Communicator → [Negotiator] → Verifier → Reporter."""
from __future__ import annotations

from typing import Any

from ..db.models import LotStatus
from ..db.repositories import LotRepo
from ..db.session import AsyncSessionLocal
from .communicator import communicator_node
from .negotiator import negotiator_node
from .planner import planner_node
from .reporter import reporter_node
from .sourcer import sourcer_node
from .state import LotState
from .verifier import verifier_node


def _should_escalate(state: LotState) -> str:
    if state.get("requires_human"):
        return "escalate"
    return "continue"


def build_graph():
    """Возвращает скомпилированный LangGraph граф."""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    g = StateGraph(LotState)
    g.add_node("planner", planner_node)
    g.add_node("sourcer", sourcer_node)
    g.add_node("communicator", communicator_node)
    g.add_node("negotiator", negotiator_node)
    g.add_node("verifier", verifier_node)
    g.add_node("reporter", reporter_node)

    g.set_entry_point("planner")
    g.add_conditional_edges(
        "planner", _should_escalate, {"escalate": END, "continue": "sourcer"}
    )
    g.add_edge("sourcer", "communicator")
    g.add_edge("communicator", "negotiator")
    g.add_edge("negotiator", "verifier")
    g.add_edge("verifier", "reporter")
    g.add_edge("reporter", END)

    return g.compile()


async def run_lot(state: LotState) -> LotState:
    """Запускает граф для одного лота. Обновляет статус в БД на каждом узле."""
    graph = build_graph()
    if graph is None:
        # Fallback — последовательный запуск без LangGraph
        return await _run_sequential(state)

    final_state: LotState = dict(state)  # type: ignore[assignment]
    async for event in graph.astream(state):
        for _node, output in event.items():
            for k, v in (output or {}).items():
                if k == "audit_events":
                    final_state.setdefault("audit_events", []).extend(v or [])
                elif k == "errors":
                    final_state.setdefault("errors", []).extend(v or [])
                else:
                    final_state[k] = v  # type: ignore[literal-required]
            await _persist_status(final_state)
    await _persist_status(final_state, finalize=True)
    return final_state


async def _run_sequential(state: LotState) -> LotState:
    out: dict[str, Any] = dict(state)
    for node in (planner_node, sourcer_node, communicator_node, negotiator_node, verifier_node, reporter_node):
        update = await node(out)  # type: ignore[arg-type]
        if update:
            for k, v in update.items():
                if k == "audit_events":
                    out.setdefault("audit_events", []).extend(v or [])
                elif k == "errors":
                    out.setdefault("errors", []).extend(v or [])
                else:
                    out[k] = v
            await _persist_status(out)
            if out.get("requires_human") and node is planner_node:
                break
    await _persist_status(out, finalize=True)
    return out  # type: ignore[return-value]


_STATUS_MAP = {
    "planned": LotStatus.planned,
    "sourcing": LotStatus.sourcing,
    "rfq_sent": LotStatus.rfq_sent,
    "responses_collected": LotStatus.responses_collected,
    "negotiating": LotStatus.negotiating,
    "verified": LotStatus.verified,
    "report_ready": LotStatus.report_ready,
    "escalated": LotStatus.escalated,
}


async def _persist_status(state: dict, *, finalize: bool = False) -> None:
    s = state.get("status")
    lot_id = state.get("lot_id")
    if not lot_id:
        return
    target = _STATUS_MAP.get(s)
    async with AsyncSessionLocal() as session:
        repo = LotRepo(session)
        if target:
            update_fields: dict[str, Any] = {
                "parsed_items": state.get("parsed_items") or [],
                "category": state.get("category"),
                "requires_human": bool(state.get("requires_human")),
                "escalation_reason": state.get("escalation_reason"),
            }
            if state.get("total_estimated_rub") is not None:
                update_fields["total_estimated_rub"] = state["total_estimated_rub"]
            await repo.update_status(lot_id, target, **update_fields)
        if finalize and state.get("report"):
            await repo.set_report(lot_id, state["report"])
