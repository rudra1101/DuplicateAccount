from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.ai.agent_service import (
    _execute_tool_calls,
    build_messages,
    extract_text_tool_calls,
)
from app.ai.config import get_ai_settings
from app.ai.providers.factory import AIProviderFactory
from app.ai.tools import create_ai_tool_registry
from app.schemas.chat import ChatResponse, ChatSource, ToolInvocationResponse


TERMINAL_ACTION_TOOLS = {
    "generate_report",
    "create_remediation_ticket",
    "navigate_app",
}


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


def _terminal_action_message(
    tool_history: list[ToolInvocationResponse],
    start_index: int,
) -> str:
    messages: list[str] = []

    for invocation in tool_history[start_index:]:
        result = invocation.result
        if not isinstance(result, dict) or not result.get("success"):
            continue
        data = result.get("data")
        if not isinstance(data, dict):
            continue
        message = str(data.get("message") or "").strip()
        if message:
            messages.append(message)

    return "\n\n".join(messages)


def run_identity_agent_stream_fast(
    *,
    db: Session,
    request,
) -> Iterator[dict[str, Any]]:
    """Single-pass Rudrix streaming with tool support.

    The previous streaming flow performed one blocking model generation to
    choose tools and then a second model generation for the answer. Ollama's
    provider already supports streaming tool calls safely, so this path uses
    that capability directly. Natural-language answers start streaming on the
    first provider call, while tool calls remain hidden and are executed before
    another iteration.

    Action-only tools (report generation, ticket creation, navigation) return a
    deterministic confirmation after execution, avoiding an unnecessary second
    LLM round-trip entirely.
    """

    settings = get_ai_settings()
    provider = AIProviderFactory.create(settings)
    registry = create_ai_tool_registry()

    selected_model = (
        settings.reasoning_model
        if request.useReasoningModel
        else settings.fast_model
    )

    messages = build_messages(request)
    definitions = registry.definitions()
    allowed_tools = {definition["name"] for definition in definitions}

    tool_history: list[ToolInvocationResponse] = []
    chat_sources: list[ChatSource] = []
    source_keys: set[tuple[int, int | None]] = set()
    final_message = ""

    stream_method = getattr(provider, "stream_chat", None)

    for iteration in range(settings.max_tool_iterations):
        yield {
            "type": "status",
            "message": (
                "Analyzing your request..."
                if iteration == 0
                else "Reviewing connected data..."
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
                        streamed_parts.append(text)
                        yield {"type": "delta", "text": text}
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

        if not tool_calls:
            fallback_calls = extract_text_tool_calls(
                provider_response.text,
                allowed_tools,
            )
            if fallback_calls:
                tool_calls = fallback_calls

        if tool_calls:
            # A native/fallback tool call should not have emitted user-visible
            # content. Keep the assistant tool-call turn for the next iteration.
            messages.append(provider_response.assistant_message)

            yield {
                "type": "status",
                "message": "Working with IdentityAI data...",
            }

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

            names = _tool_names(tool_calls)
            if names and names.issubset(TERMINAL_ACTION_TOOLS):
                action_message = _terminal_action_message(
                    tool_history,
                    history_start,
                )
                if action_message:
                    final_message = action_message
                    yield {"type": "delta", "text": action_message}
                    break

            # A data lookup requires the model to synthesize the result, so run
            # another streamed iteration with the tool messages now in context.
            continue

        # Natural-language response was already streamed when supported. For a
        # provider without streaming support, emit the completed text once.
        final_message = (provider_response.text or "").strip()
        if not streamed_parts and final_message:
            yield {"type": "delta", "text": final_message}

        if not final_message:
            final_message = "No response was generated."
        break
    else:
        final_message = (
            "The assistant reached the maximum number of tool operations."
        )
        yield {"type": "delta", "text": final_message}

    yield {
        "type": "done",
        "response": ChatResponse(
            conversationId=(
                request.conversationId
                or str(uuid.uuid4())
            ),
            message=final_message,
            model=selected_model,
            toolsUsed=tool_history,
            sources=chat_sources,
        ),
    }
