"""Optional LLM-backed planner.

When ``MANDATE_LLM_PROVIDER`` is ``anthropic`` or ``openai`` and the matching key
is set, the goal + tool specs are sent to the model with structured-output tool
selection. The model returns a JSON array of ``{tool, arguments}`` calls.

This module is imported lazily by the orchestrator and any failure falls back to
the deterministic planner, so the SDKs are optional dependencies.
"""

from __future__ import annotations

import json

from app.agent.tools import TOOL_SPECS
from app.core.config import settings

_SYSTEM = (
    "You are Mandate, an autonomous CFO agent for crypto-native organizations. "
    "Given a goal, choose a short ordered sequence of tool calls from the provided "
    "tools to accomplish it safely under the treasury policy. Respond ONLY with a "
    "JSON array of objects {\"tool\": str, \"arguments\": object}. No prose."
)


def _prompt(goal: str) -> str:
    return (
        f"Tools:\n{json.dumps(TOOL_SPECS, indent=2)}\n\n"
        f"Goal: {goal}\n\n"
        "Return the JSON array of tool calls."
    )


def plan_with_llm(goal: str) -> list[dict] | None:
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return _anthropic(goal)
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return _openai(goal)
    return None


def _extract_json_array(text: str) -> list[dict] | None:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return [c for c in parsed if isinstance(c, dict) and "tool" in c]


def _anthropic(goal: str) -> list[dict] | None:
    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.llm_model,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _prompt(goal)}],
    )
    text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
    return _extract_json_array(text)


def _openai(goal: str) -> list[dict] | None:
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _prompt(goal)},
        ],
    )
    return _extract_json_array(resp.choices[0].message.content or "")
