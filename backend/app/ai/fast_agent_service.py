from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.ai.agent_core import (
    AgentState,
    CapabilityCatalog,
    hydrate_state_from_history,
    reduce_tool_result,
    render_state_for_planner,
)
from app.ai.agent_service import (
    _execute_tool_calls,
    build_messages,
    extract_text_tool_calls,
)
from app.ai.config import get_ai_settings
from app.ai.providers.factory import AIProviderFactory
from app.ai.tools import create_ai_tool_registry
from app.schemas.chat import ChatResponse, ChatSource, ToolInvocationResponse


MAX_CONTEXT_MESSAGES = 12

_TRIVIAL_CONVERSATION = {
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "good morning",
    "good afternoon",
    "good evening",
}


def _trim_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(messages) <= MAX_CONTEXT_MESSAGES + 1:
        return messages
    return [messages[0], *messages[-MAX_CONTEXT_MESSAGES:]]


def _is_trivial_conversation(request) -> bool:
    current = " ".join(str(request.message or "").strip().lower().split())
    return current.rstrip("!?.") in _TRIVIAL_CONVERSATION


def _select_definitions(
    definitions: list[dict[str, Any]],
    request,
) -> list[dict[str, Any]]:
    """Return the complete authorized capability surface for agent turns.

    This intentionally does not inspect domain keywords. Tool selection belongs to
    the model operating over tool schemas and grounded conversation state.
    """

    if _is_trivial_conversation(request):
        return []
    return definitions


def _is_fast_path_selection(
    definitions: list[dict[str, Any]],
    catalog: CapabilityCatalog,
) -> bool:
    """Compatibility helper retained for tests/metrics, not runtime routing."""

    names = {
        str(definition.get("name") or "")
        for definition in definitions
        if definition.get("name")
    }
    if not names or len(names) != 1:
        return False
    fast_names = {
        capability.name
        for capability in catalog.capabilities()
        if capability.fast_path
    }
    return names.issubset(fast_names)


def _initial_agent_state(
    *,
    persisted_state: dict[str, Any] | None,
    history: list[Any],
) -> AgentState:
    if isinstance(persisted_state, dict) and persisted_state:
        try:
            return AgentState.model_validate(persisted_state)
        except Exception:
            pass
    return hydrate_state_from_history(history)


def _state_instruction(state: AgentState) -> str:
    return (
        render_state_for_planner(state)
        + " This state is authoritative because it was produced by successful tools. "
        "Resolve human references from it when unambiguous. Do not ask for an internal "
        "ID that is already present here. Decide the next tool from the exposed tool "
        "schemas, or answer when the user's goal is complete."
    )


def _tool_names(tool_calls: list[Any]) -> set[str]:
    names: set[str] = set()
    for call in tool_calls:
        if isinstance(call, dict):
            name = call.get("name")
        else:
            name = getattr(call, "name", None)
        if isinstance(name, str) and name:
            names.add(name)
    return names


def run_identity_agent_stream_fast(
    *,
    db: Session,
    request,
    persisted_state: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Run Rudrix as one generic tool-using agent loop.

    There is no domain keyword router here. Every non-trivial turn receives the full
    RBAC-filtered IdentityAI capability surface. The model chooses and chains tools,
    while backend tools remain authoritative for facts, permissions, and side effects.
    """

    settings = get_ai_settings()
    provider = AIProviderFactory.create(settings)
    registry = create_ai_tool_registry()
    catalog = CapabilityCatalog(registry)

    selected_model = (
        settings.reasoning_model
        if request.useReasoningModel
        else settings.fast_model
    )

    state = _initial_agent_state(
        persisted_state=persisted_state,
        history=list(request.history or []),
    )

    messages = _trim_messages(build_messages(request))
    messages.insert(
        1,
        {
            "role": "system",
            "content": _state_instruction(state),
        },
    )

    all_definitions = registry.definitions()
    definitions = _select_definitions(all_definitions, request)
    allowed_tools = {
        str(definition.get("name") or "")
        for definition in definitions
        if definition.get("name")
    }

    tool_history: list[ToolInvocationResponse] = []
    chat_sources: list[ChatSource] = []
    source_keys: set[tuple[int, int | None]] = set()
    final_message = ""

    stream_method = getattr(provider, "stream_chat", None)

    for iteration in range(settings.max_tool_iterations):
        if definitions:
            yield {
                "type": "status",
                "message": (
                    "Working on your request..."
                    if iteration == 0
                    else "Continuing with IdentityAI data..."
                ),
            }

        provider_response = None
        streamed_parts: list[str] = []

        if callable(stream_method):
            for provider_event in stream_method(
                model=selected_model,
                messages=messages,
                tools=definitions,
            ):
                event_type = provider_event.get("type")
                if event_type == "delta":
                    text = str(provider_event.get("text") or "")
                    if text:
                        # Buffer intermediate model prose. If this turn produces a tool
                        # call, the prose is planning chatter and must not leak to users.
                        streamed_parts.append(text)
                    continue
                if event_type == "result":
                    provider_response = provider_event.get("response")
        else:
            provider_response = provider.chat(
                model=selected_model,
                messages=messages,
                tools=definitions,
            )

        if provider_response is None:
            raise RuntimeError("AI provider did not return a final response.")

        tool_calls = list(provider_response.tool_calls or [])
        if not tool_calls and allowed_tools:
            fallback_calls = extract_text_tool_calls(
                provider_response.text,
                allowed_tools,
            )
            if fallback_calls:
                tool_calls = fallback_calls

        if tool_calls:
            messages.append(provider_response.assistant_message)
            yield {"type": "status", "message": "Using IdentityAI capabilities..."}

            history_start = len(tool_history)
            _execute_tool_calls(
                db=db,
                registry=registry,
                messages=messages,
                tool_calls=tool_calls,
                tool_history=tool_history,
                chat_sources=chat_sources,
                source_keys=source_keys,
            )

            for invocation in tool_history[history_start:]:
                state = reduce_tool_result(
                    state,
                    tool_name=invocation.name,
                    tool_result=invocation.result,
                )

            messages.append(
                {
                    "role": "system",
                    "content": _state_instruction(state),
                }
            )
            continue

        final_message = (provider_response.text or "").strip()
        if not final_message and streamed_parts:
            final_message = "".join(streamed_parts).strip()
        if not final_message:
            final_message = "No response was generated."

        yield {"type": "delta", "text": final_message}
        break
    else:
        final_message = "The assistant reached the maximum number of tool operations."
        yield {"type": "delta", "text": final_message}

    yield {
        "type": "done",
        "response": ChatResponse(
            conversationId=(request.conversationId or str(uuid.uuid4())),
            message=final_message,
            model=selected_model,
            toolsUsed=tool_history,
            sources=chat_sources,
        ),
        "agentState": state.model_dump(exclude_none=True),
    }
