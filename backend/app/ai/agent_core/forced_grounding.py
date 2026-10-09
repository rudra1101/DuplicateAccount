from __future__ import annotations

from typing import Any

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


def force_grounding_tool_calls(
    *,
    provider,
    model: str,
    user_message: str,
    grounded_state: str,
    definitions: list[dict[str, Any]],
) -> list[Any]:
    """Constrained second-chance planner for models that answer without grounding."""

    if not definitions:
        return []

    messages = [
        {
            "role": "system",
            "content": (
                "You are the grounding planner for IdentityAI. Do not answer the user. "
                "Select exactly one supplied read-only capability that can ground the "
                "request and provide arguments inferred from the request and grounded "
                "state. Prefer live-data capabilities for current records/status and "
                "knowledge capabilities for explanatory product/document questions. "
                "Use native tool calling when available. Otherwise output only one JSON "
                "object with keys name and arguments. Never invent internal IDs."
            ),
        },
        {
            "role": "user",
            "content": f"Request:\n{user_message}\n\nGrounded state:\n{grounded_state}",
        },
    ]

    response = provider.chat(model=model, messages=messages, tools=definitions)
    native_calls = list(response.tool_calls or [])
    if native_calls:
        return native_calls[:1]

    allowed = {
        str(definition.get("name") or "")
        for definition in definitions
        if definition.get("name")
    }
    return extract_text_tool_calls(response.text, allowed)[:1]
