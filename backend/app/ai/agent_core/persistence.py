from __future__ import annotations

from typing import Iterable

from pydantic import ValidationError

from app.ai.agent_core.models import AgentState
from app.ai.agent_core.state import reduce_tool_result
from app.schemas.chat import ToolInvocationResponse


def load_agent_state(raw_state) -> AgentState:
    """Load persisted state defensively.

    Conversation state must never make chat unusable if an older deployment or
    manual database change left malformed JSON behind. Invalid state therefore
    falls back to an empty grounded state rather than being handed to the model.
    """
    if not isinstance(raw_state, dict):
        return AgentState()
    try:
        return AgentState.model_validate(raw_state)
    except (ValidationError, TypeError, ValueError):
        return AgentState()


def reduce_tool_history(
    state: AgentState,
    tools: Iterable[ToolInvocationResponse],
) -> AgentState:
    """Advance conversation state using only successful grounded tool outputs."""
    updated = state
    for invocation in tools:
        updated = reduce_tool_result(
            updated,
            tool_name=invocation.name,
            tool_result=invocation.result,
        )
    return updated


def dump_agent_state(state: AgentState) -> dict:
    """Return JSON-safe state for the conversation record."""
    return state.compact()


def agent_state_system_message(state: AgentState) -> dict[str, str] | None:
    """Create compact authoritative context for the planner/model.

    This is general agent context, not sentence-specific prompt routing. It lets
    referential language such as "it", "this account", "the duplicate", and
    "those results" reuse grounded entities without reparsing assistant prose.
    """
    compact = state.compact()
    if not compact:
        return None
    return {
        "role": "system",
        "content": (
            "Grounded IdentityAI conversation state follows. Treat these "
            "identifiers and attributes as authoritative product context for "
            "referential user language. Do not invent missing values. Re-check "
            "live data with tools when freshness matters.\n"
            f"{compact}"
        ),
    }
