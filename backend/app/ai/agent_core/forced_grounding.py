from __future__ import annotations

from typing import Any

from app.ai.agent_core.capability_retriever import CapabilityRetriever
from app.ai.agent_core.models import AgentCapability, CapabilityKind
from app.ai.agent_service import extract_text_tool_calls


SAFE_GROUNDING_KINDS = {CapabilityKind.READ, CapabilityKind.KNOWLEDGE}


def safe_grounding_definitions(
    definitions: list[dict[str, Any]],
    capabilities: list[AgentCapability],
) -> list[dict[str, Any]]:
    safe_names = {
        capability.name
        for capability in capabilities
        if capability.kind in SAFE_GROUNDING_KINDS and not capability.destructive
    }
    return [
        definition
        for definition in definitions
        if str(definition.get("name") or "") in safe_names
    ]


def primary_grounding_definition(
    definitions: list[dict[str, Any]],
    user_message: str,
) -> dict[str, Any] | None:
    """Choose the best safe capability from its contract, not from prompt routing."""

    if not definitions:
        return None

    selected = CapabilityRetriever(definitions).select(
        str(user_message or ""),
        limit=1,
    )
    return selected[0] if selected else None


def force_grounding_tool_calls(
    *,
    provider,
    model: str,
    user_message: str,
    grounded_state: str,
    definitions: list[dict[str, Any]],
) -> list[Any]:
    """Constrained second-chance planner for models that answer without grounding.

    Capability choice is deterministic from the retrieved tool contracts. The model
    only fills arguments for that single selected read/knowledge capability. This
    prevents a small local model from choosing an unrelated knowledge tool merely
    because several safe grounding tools were exposed at once.
    """

    selected = primary_grounding_definition(definitions, user_message)
    if selected is None:
        return []

    selected_name = str(selected.get("name") or "")
    if not selected_name:
        return []

    messages = [
        {
            "role": "system",
            "content": (
                "You are the argument planner for one preselected IdentityAI capability. "
                "Do not answer the user and do not choose another capability. Fill the "
                "arguments for the supplied capability using only the user's request and "
                "grounded state. Use native tool calling when available. Otherwise output "
                "only one JSON object with keys name and arguments. Never invent internal "
                "IDs or values not supported by the request/state."
            ),
        },
        {
            "role": "user",
            "content": f"Request:\n{user_message}\n\nGrounded state:\n{grounded_state}",
        },
    ]

    response = provider.chat(model=model, messages=messages, tools=[selected])
    native_calls = [
        call
        for call in list(response.tool_calls or [])
        if getattr(call, "name", None) == selected_name
    ]
    if native_calls:
        return native_calls[:1]

    return extract_text_tool_calls(response.text, {selected_name})[:1]
