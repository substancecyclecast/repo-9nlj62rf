"""LLM-backed agentic planner with native function calling.

When ``MANDATE_LLM_PROVIDER`` is ``anthropic`` or ``openai`` and the matching key
is set, the agent runs a multi-step tool-use loop:

    model → tool_call → observation → model → tool_call → ... → done

Each step is recorded as an ``AgentRunStep`` for full auditability. The model
uses the provider's native function-calling API (Anthropic tools / OpenAI tools)
rather than JSON-in-text extraction.

This module is imported lazily by the orchestrator and any failure falls back to
the deterministic planner, so the SDKs are optional dependencies.
"""

from __future__ import annotations

import json

from app.agent.tools import TOOL_SPECS
from app.core.config import settings

MAX_TOOL_STEPS = 10

_SYSTEM = (
    "You are Mandate, an autonomous CFO agent for crypto-native organizations. "
    "You have access to treasury management tools. Given a goal, use the tools "
    "to accomplish it safely under the treasury policy. Call tools as needed. "
    "When you have enough information to provide a final answer or have completed "
    "the requested action, stop calling tools and provide a summary."
)


def _build_tool_definitions_anthropic() -> list[dict]:
    """Convert TOOL_SPECS to Anthropic tools format."""
    tools = []
    for spec in TOOL_SPECS:
        properties = {}
        for param_name, param_desc in spec.get("parameters", {}).items():
            param_type = "string"
            if "number" in str(param_desc).lower():
                param_type = "number"
            elif "boolean" in str(param_desc).lower():
                param_type = "boolean"
            elif "array" in str(param_desc).lower():
                param_type = "array"
            properties[param_name] = {
                "type": param_type,
                "description": str(param_desc),
            }
        tools.append({
            "name": spec["name"],
            "description": spec["description"],
            "input_schema": {
                "type": "object",
                "properties": properties,
            },
        })
    return tools


def _build_tool_definitions_openai() -> list[dict]:
    """Convert TOOL_SPECS to OpenAI function calling format."""
    tools = []
    for spec in TOOL_SPECS:
        properties = {}
        for param_name, param_desc in spec.get("parameters", {}).items():
            param_type = "string"
            if "number" in str(param_desc).lower():
                param_type = "number"
            elif "boolean" in str(param_desc).lower():
                param_type = "boolean"
            properties[param_name] = {
                "type": param_type,
                "description": str(param_desc),
            }
        tools.append({
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                },
            },
        })
    return tools


def plan_with_llm(goal: str) -> list[dict] | None:
    """Run a multi-step agentic loop and return the sequence of tool calls made."""
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return _anthropic_loop(goal)
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return _openai_loop(goal)
    return None


def _anthropic_loop(goal: str) -> list[dict] | None:
    """Multi-step tool-use loop via Anthropic's native function calling."""
    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tools = _build_tool_definitions_anthropic()
    messages: list[dict] = [{"role": "user", "content": goal}]
    collected_calls: list[dict] = []

    for _ in range(MAX_TOOL_STEPS):
        resp = client.messages.create(
            model=settings.llm_model,
            max_tokens=2048,
            system=_SYSTEM,
            tools=tools,
            messages=messages,
        )

        # Check if the model wants to use tools
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            break

        # Build assistant message with all content blocks
        messages.append({"role": "assistant", "content": resp.content})

        # Process each tool call and collect results
        tool_results = []
        for tool_use in tool_uses:
            collected_calls.append({
                "tool": tool_use.name,
                "arguments": tool_use.input,
            })
            # Return a placeholder observation — the orchestrator will execute
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": json.dumps({"status": "will_be_executed_by_orchestrator"}),
            })

        messages.append({"role": "user", "content": tool_results})

        # If model signaled stop, break
        if resp.stop_reason == "end_turn":
            break

    return collected_calls if collected_calls else None


def _openai_loop(goal: str) -> list[dict] | None:
    """Multi-step tool-use loop via OpenAI's native function calling."""
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=settings.openai_api_key)
    tools = _build_tool_definitions_openai()
    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": goal},
    ]
    collected_calls: list[dict] = []

    for _ in range(MAX_TOOL_STEPS):
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        choice = resp.choices[0]
        message = choice.message

        if not message.tool_calls:
            break

        # Add assistant message
        messages.append(message.model_dump())

        # Process tool calls
        for tool_call in message.tool_calls:
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}

            collected_calls.append({
                "tool": tool_call.function.name,
                "arguments": args,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"status": "will_be_executed_by_orchestrator"}),
            })

        if choice.finish_reason == "stop":
            break

    return collected_calls if collected_calls else None
