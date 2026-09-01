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

# Keeping fewer historical messages materially reduces local-model prompt
# evaluation time while preserving enough context for natural follow-ups.
MAX_CONTEXT_MESSAGES = 12


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


def _trim_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(messages) <= MAX_CONTEXT_MESSAGES + 1:
        return messages

    # Always preserve the system prompt and the most recent conversation turns.
    return [messages[0], *messages[-MAX_CONTEXT_MESSAGES:]]


def _routing_text(request) -> str:
    pieces = [str(request.message or "")]
    for message in list(request.history or [])[-4:]:
        pieces.append(str(message.content or ""))
    return " ".join(pieces).lower()


def _select_definitions(
    definitions: list[dict[str, Any]],
    request,
) -> list[dict[str, Any]]:
    """Send only likely-relevant tools to the local model.

    Tool schemas consume prompt tokens and increase tool-selection latency.
    Routing is deliberately broad: overlapping domains can expose several tools,
    while a normal conversational/IAM explanation can run with no tool schema.
    """

    text = _routing_text(request)
    selected: set[str] = set()

    def has(*terms: str) -> bool:
        return any(term in text for term in terms)

    if has(
        "report", "export", "csv", "download", "spreadsheet",
    ):
        selected.add("generate_report")

    if has(
        "ticket", "service desk", "servicedesk", "remediation",
        "remediate", "disable account", "delete account",
    ):
        selected.update(
            {
                "search_remediation_items",
                "create_remediation_ticket",
            }
        )

    if has(
        "navigate", "take me", "go to", "open the", "open ",
        "show page", "page for", "screen",
    ):
        selected.add("navigate_app")

    if has(
        "dashboard", "overall", "system summary", "total accounts",
        "total applications", "how many accounts", "how many applications",
        "how many duplicate", "most duplicates", "high confidence matches",
    ):
        selected.add("get_dashboard_summary")

    if has(
        "integration", "connector", "source connection",
    ):
        selected.update(
            {
                "list_integrations",
                "get_integration_details",
            }
        )

    if has(
        "execution", "job", "scan status", "latest scan", "run status",
        "running", "failed run", "failed execution", "operations",
    ):
        selected.update(
            {
                "get_operations_summary",
                "search_operations",
                "get_latest_execution",
                "get_execution_details",
            }
        )

    if has(
        "duplicate", "confidence", "review", "candidate", "match",
    ):
        selected.update(
            {
                "get_duplicate_summary",
                "search_duplicate_groups",
                "get_duplicate_group_details",
                "get_review_statistics",
                "get_confidence_breakdown",
            }
        )

    if has(
        "training label", "training data", "ml training", "model training",
    ):
        selected.add("get_training_label_summary")

    if has(
        "knowledge", "document", "policy", "procedure", "runbook",
        "standard", "manual", "documentation", "guidance",
    ):
        selected.update(
            {
                "search_knowledge_base",
                "list_knowledge_documents",
            }
        )

    if not selected:
        return []

    return [
        definition
        for definition in definitions
        if str(definition.get("name") or "") in selected
    ]


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

    messages = _trim_messages(build_messages(request))
    definitions = _select_definitions(registry.definitions(), request)
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

        if not tool_calls and allowed_tools:
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
