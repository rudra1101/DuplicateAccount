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
    """Parse an optional explicit planner response.

    Kept as a reusable contract for future reasoning-model planning, MCP planners,
    or offline evaluation. The production fast path currently uses native model
    tool calling directly to avoid an extra blocking model request.
    """

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
    """Expose the authorized capability surface to the native tool-calling agent.

    Rudrix's fast runtime deliberately avoids a separate planner-model round trip.
    For non-trivial requests it gives the model the complete RBAC-filtered capability
    catalog and lets native tool calling choose and chain the required tools inside
    the existing agent loop. This keeps the behavior agentic without doubling first
    token latency. The unused arguments are part of the stable planner contract so a
    reasoning planner or MCP-backed planner can be introduced later without changing
    callers.
    """

    del provider, model, user_message, state

    names = tuple(
        str(item.get("name") or "")
        for item in catalog.compact_for_planner()
        if item.get("name")
    )
    return CapabilityPlan(capabilities=names)
