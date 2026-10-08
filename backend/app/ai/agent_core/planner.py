from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.ai.agent_core.capabilities import CapabilityCatalog
from app.ai.agent_core.models import AgentState


@dataclass(frozen=True)
class CapabilityPlan:
    capabilities: tuple[str, ...]
    goal: str = ""
    needs_clarification: bool = False


def _extract_json_object(text: str) -> dict[str, Any] | None:
    value = str(text or "").strip()
    if not value:
        return None

    decoder = json.JSONDecoder()
    for index, char in enumerate(value):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def parse_capability_plan(text: str, allowed_names: set[str]) -> CapabilityPlan:
    payload = _extract_json_object(text)
    if payload is None:
        return CapabilityPlan(capabilities=())

    raw_names = payload.get("capabilities")
    if not isinstance(raw_names, list):
        raw_names = []

    names: list[str] = []
    for raw_name in raw_names:
        name = str(raw_name or "").strip()
        if name and name in allowed_names and name not in names:
            names.append(name)
        if len(names) >= 6:
            break

    return CapabilityPlan(
        capabilities=tuple(names),
        goal=str(payload.get("goal") or "").strip(),
        needs_clarification=bool(payload.get("needsClarification", False)),
    )


def plan_capabilities(
    *,
    provider,
    model: str,
    user_message: str,
    catalog: CapabilityCatalog,
    state: AgentState,
) -> CapabilityPlan:
    """Use the model as a capability planner, not a sentence router.

    The planner sees the RBAC-filtered capability catalog and grounded structured
    conversation state. It chooses capabilities that may be needed to satisfy the
    user's goal. Tool execution and authorization remain server-side.
    """

    capabilities = catalog.compact_for_planner()
    allowed_names = {
        str(item.get("name") or "")
        for item in capabilities
        if item.get("name")
    }

    compact_capabilities = [
        {
            "name": item.get("name"),
            "domain": item.get("domain"),
            "kind": item.get("kind"),
            "description": str(item.get("description") or "")[:260],
        }
        for item in capabilities
    ]

    planner_system = (
        "You are the Rudrix capability planner for the IdentityAI product. "
        "Choose the minimum set of available capabilities required to accomplish "
        "the user's goal. You may choose multiple capabilities for multi-step work. "
        "Use grounded conversation state to understand references such as this, it, "
        "that account, the duplicate, those results, or the last execution. "
        "For product facts or actions, prefer live capabilities over assumptions. "
        "Use knowledge capabilities for documentation, policy, procedure, or how-to "
        "questions. Never invent a capability. Return JSON only in this exact shape: "
        '{"goal":"short goal","capabilities":["tool_name"],"needsClarification":false}. '
        "Return an empty capabilities list only when the request is ordinary conversation "
        "that does not require IdentityAI live data, product knowledge, navigation, or action."
    )

    context = {
        "groundedState": state.compact(),
        "capabilities": compact_capabilities,
        "userRequest": str(user_message or ""),
    }

    response = provider.chat(
        model=model,
        messages=[
            {"role": "system", "content": planner_system},
            {"role": "user", "content": json.dumps(context, default=str)},
        ],
        tools=[],
    )
    return parse_capability_plan(response.text, allowed_names)
