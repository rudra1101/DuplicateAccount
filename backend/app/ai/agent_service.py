import json
import uuid
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.ai.config import (
    get_ai_settings,
)
from app.ai.prompts import (
    IDENTITY_OPERATIONS_INSTRUCTIONS,
)
from app.ai.providers.factory import (
    AIProviderFactory,
)
from app.ai.tools import (
    create_ai_tool_registry,
)
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    ToolInvocationResponse,
)


def build_messages(
    request: ChatRequest,
) -> list[dict[str, Any]]:
    messages: list[
        dict[str, Any]
    ] = [
        {
            "role": "system",
            "content": (
                IDENTITY_OPERATIONS_INSTRUCTIONS
            ),
        }
    ]

    for message in request.history:
        messages.append(
            {
                "role":
                    message.role,
                "content":
                    message.content,
            }
        )

    messages.append(
        {
            "role": "user",
            "content":
                request.message,
        }
    )

    return messages


def extract_text_tool_calls(
    content: str,
    allowed_tools: set[str],
) -> list[dict[str, Any]]:
    if not content:
        return []

    decoder = json.JSONDecoder()

    tool_calls: list[
        dict[str, Any]
    ] = []

    index = 0

    while index < len(content):
        start = content.find(
            "{",
            index,
        )

        if start == -1:
            break

        try:
            value, consumed = (
                decoder.raw_decode(
                    content[start:]
                )
            )
            index = (
                start
                + consumed
            )
        except json.JSONDecodeError:
            index = (
                start
                + 1
            )
            continue

        if not isinstance(
            value,
            dict,
        ):
            continue

        name = value.get(
            "name"
        )

        arguments = (
            value.get(
                "arguments"
            )
            or value.get(
                "parameters"
            )
        )

        if (
            isinstance(
                name,
                str,
            )
            and name
            in allowed_tools
            and isinstance(
                arguments,
                dict,
            )
        ):
            tool_calls.append(
                {
                    "name":
                        name,
                    "arguments":
                        arguments,
                }
            )

    return tool_calls


def normalize_tool_arguments(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(
        arguments
    )

    if tool_name == (
        "get_confidence_breakdown"
    ):
        minimum_confidence = (
            normalized.get(
                "minimum_confidence"
            )
        )

        if minimum_confidence is not None:
            try:
                normalized[
                    "minimum_confidence"
                ] = float(
                    minimum_confidence
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

    if tool_name == (
        "search_knowledge_base"
    ):
        limit = normalized.get(
            "limit",
            5,
        )

        try:
            limit = int(
                limit
            )
        except (
            TypeError,
            ValueError,
        ):
            limit = 5

        normalized[
            "limit"
        ] = max(
            1,
            min(
                limit,
                8,
            ),
        )

        minimum_similarity = (
            normalized.get(
                "minimum_similarity",
                0.50,
            )
        )

        try:
            minimum_similarity = float(
                minimum_similarity
            )
        except (
            TypeError,
            ValueError,
        ):
            minimum_similarity = 0.50

        normalized[
            "minimum_similarity"
        ] = max(
            0.0,
            min(
                minimum_similarity,
                1.0,
            ),
        )

        document_id = normalized.get(
            "document_id"
        )

        if isinstance(
            document_id,
            str,
        ):
            cleaned_document_id = (
                document_id
                .strip()
                .lower()
            )

            if cleaned_document_id in {
                "",
                "null",
                "none",
            }:
                normalized[
                    "document_id"
                ] = None
            else:
                try:
                    normalized[
                        "document_id"
                    ] = int(
                        document_id
                    )
                except ValueError:
                    normalized[
                        "document_id"
                    ] = None

    return normalized


def extract_chat_sources(
    *,
    tool_name: str,
    tool_result: dict[str, Any],
) -> list[ChatSource]:
    if tool_name != (
        "search_knowledge_base"
    ):
        return []

    if not tool_result.get(
        "success"
    ):
        return []

    data = tool_result.get(
        "data"
    )

    if not isinstance(
        data,
        dict,
    ):
        return []

    raw_sources = data.get(
        "sources"
    )

    if not isinstance(
        raw_sources,
        list,
    ):
        return []

    sources: list[
        ChatSource
    ] = []

    seen: set[
        tuple[
            int,
            int | None,
        ]
    ] = set()

    for raw_source in raw_sources:
        if not isinstance(
            raw_source,
            dict,
        ):
            continue

        document_id = (
            raw_source.get(
                "documentId"
            )
        )

        document_name = (
            raw_source.get(
                "documentName"
            )
        )

        page_number = (
            raw_source.get(
                "pageNumber"
            )
        )

        if (
            document_id is None
            or not document_name
        ):
            continue

        try:
            document_id = int(
                document_id
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if page_number is not None:
            try:
                page_number = int(
                    page_number
                )
            except (
                TypeError,
                ValueError,
            ):
                page_number = None

        key = (
            document_id,
            page_number,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        sources.append(
            ChatSource(
                documentId=
                    document_id,
                documentName=
                    str(
                        document_name
                    ),
                pageNumber=
                    page_number,
            )
        )

    return sources


def _execute_tool_calls(
    *,
    db: Session,
    registry: Any,
    messages: list[
        dict[str, Any]
    ],
    tool_calls: list[Any],
    tool_history: list[
        ToolInvocationResponse
    ],
    chat_sources: list[
        ChatSource
    ],
    source_keys: set[
        tuple[
            int,
            int | None,
        ]
    ],
) -> None:
    for tool_call in tool_calls:
        if isinstance(
            tool_call,
            dict,
        ):
            tool_name = (
                tool_call[
                    "name"
                ]
            )
            tool_arguments = (
                tool_call[
                    "arguments"
                ]
            )
        else:
            tool_name = (
                tool_call.name
            )
            tool_arguments = (
                tool_call.arguments
            )

        if not isinstance(
            tool_arguments,
            dict,
        ):
            tool_arguments = {}

        tool_arguments = (
            normalize_tool_arguments(
                tool_name,
                tool_arguments,
            )
        )

        try:
            result = (
                registry.execute(
                    name=
                        tool_name,
                    db=db,
                    arguments=
                        tool_arguments,
                )
            )

            tool_result = {
                "success":
                    True,
                "data":
                    result,
            }

        except Exception as exc:
            tool_result = {
                "success":
                    False,
                "error":
                    str(exc),
            }

        tool_history.append(
            ToolInvocationResponse(
                name=
                    tool_name,
                arguments=
                    tool_arguments,
                result=
                    tool_result,
            )
        )

        discovered_sources = (
            extract_chat_sources(
                tool_name=
                    tool_name,
                tool_result=
                    tool_result,
            )
        )

        for source in (
            discovered_sources
        ):
            key = (
                source.documentId,
                source.pageNumber,
            )

            if key in source_keys:
                continue

            source_keys.add(
                key
            )

            chat_sources.append(
                source
            )

        messages.append(
            {
                "role":
                    "tool",
                "tool_name":
                    tool_name,
                "content":
                    json.dumps(
                        tool_result,
                        default=str,
                    ),
            }
        )


def run_identity_agent(
    *,
    db: Session,
    request: ChatRequest,
) -> ChatResponse:
    """
    Existing non-streaming API path.
    Kept for regenerate/title/backward compatibility.
    """
    settings = (
        get_ai_settings()
    )

    provider = (
        AIProviderFactory.create(
            settings
        )
    )

    registry = (
        create_ai_tool_registry()
    )

    selected_model = (
        settings.reasoning_model
        if request.useReasoningModel
        else settings.fast_model
    )

    messages = build_messages(
        request
    )

    tool_history: list[
        ToolInvocationResponse
    ] = []

    chat_sources: list[
        ChatSource
    ] = []

    source_keys: set[
        tuple[
            int,
            int | None,
        ]
    ] = set()

    final_message = ""

    definitions = (
        registry.definitions()
    )

    for _ in range(
        settings.max_tool_iterations
    ):
        provider_response = (
            provider.chat(
                model=
                    selected_model,
                messages=
                    messages,
                tools=
                    definitions,
            )
        )

        messages.append(
            provider_response
            .assistant_message
        )

        tool_calls = list(
            provider_response
            .tool_calls
            or []
        )

        if not tool_calls:
            allowed_tools = {
                definition["name"]
                for definition
                in definitions
            }

            fallback_calls = (
                extract_text_tool_calls(
                    provider_response.text,
                    allowed_tools,
                )
            )

            if fallback_calls:
                tool_calls = (
                    fallback_calls
                )

        if not tool_calls:
            final_message = (
                provider_response
                .text
                .strip()
                or "No response was generated."
            )
            break

        _execute_tool_calls(
            db=db,
            registry=registry,
            messages=messages,
            tool_calls=
                tool_calls,
            tool_history=
                tool_history,
            chat_sources=
                chat_sources,
            source_keys=
                source_keys,
        )

    else:
        final_message = (
            "The assistant reached the maximum "
            "number of tool operations."
        )

    return ChatResponse(
        conversationId=(
            request.conversationId
            or str(
                uuid.uuid4()
            )
        ),
        message=
            final_message,
        model=
            selected_model,
        toolsUsed=
            tool_history,
        sources=
            chat_sources,
    )


def run_identity_agent_stream(
    *,
    db: Session,
    request: ChatRequest,
) -> Iterator[
    dict[str, Any]
]:
    """
    Hybrid tool + streaming agent.

    Tool-selection turns use the normal non-streaming provider call.
    This is the most reliable way to preserve Ollama tool calling.

    Once the model no longer requests a tool, the final user-facing
    answer is generated again with tools disabled and stream=True.
    Only that final answer is streamed to the browser.

    Yields:
    {"type": "status", "message": "..."}
    {"type": "delta", "text": "..."}
    {"type": "done", "response": ChatResponse}
    """
    settings = (
        get_ai_settings()
    )

    provider = (
        AIProviderFactory.create(
            settings
        )
    )

    registry = (
        create_ai_tool_registry()
    )

    selected_model = (
        settings.reasoning_model
        if request.useReasoningModel
        else settings.fast_model
    )

    messages = build_messages(
        request
    )

    tool_history: list[
        ToolInvocationResponse
    ] = []

    chat_sources: list[
        ChatSource
    ] = []

    source_keys: set[
        tuple[
            int,
            int | None,
        ]
    ] = set()

    definitions = (
        registry.definitions()
    )

    allowed_tools = {
        definition["name"]
        for definition
        in definitions
    }

    final_message = ""

    stream_method = getattr(
        provider,
        "stream_chat",
        None,
    )

    for iteration in range(
        settings.max_tool_iterations
    ):
        if iteration == 0:
            yield {
                "type": "status",
                "message":
                    "Analyzing your request...",
            }
        else:
            yield {
                "type": "status",
                "message":
                    "Reviewing connected data...",
            }

        # -----------------------------------------------------
        # Phase 1: reliable tool-selection turn (stream=False)
        # -----------------------------------------------------
        provider_response = (
            provider.chat(
                model=selected_model,
                messages=messages,
                tools=definitions,
            )
        )

        tool_calls = list(
            provider_response.tool_calls
            or []
        )

        # Defensive fallback for local models that returned a
        # textual JSON tool request rather than native tool_calls.
        if not tool_calls:
            fallback_calls = (
                extract_text_tool_calls(
                    provider_response.text,
                    allowed_tools,
                )
            )

            if fallback_calls:
                tool_calls = (
                    fallback_calls
                )

        if tool_calls:
            # Preserve the assistant tool-call turn before appending
            # tool result messages.
            messages.append(
                provider_response
                .assistant_message
            )

            yield {
                "type": "status",
                "message":
                    "Checking connected data...",
            }

            _execute_tool_calls(
                db=db,
                registry=registry,
                messages=messages,
                tool_calls=tool_calls,
                tool_history=tool_history,
                chat_sources=chat_sources,
                source_keys=source_keys,
            )

            continue

        # -----------------------------------------------------
        # Phase 2: no tool needed anymore. Generate the final
        # answer with tools DISABLED and true Ollama streaming.
        # -----------------------------------------------------
        yield {
            "type": "status",
            "message":
                "Preparing response...",
        }

        if not callable(
            stream_method
        ):
            # Fallback for a provider that does not implement
            # streaming. Use the already generated natural answer.
            final_message = (
                provider_response.text.strip()
                or "No response was generated."
            )

            yield {
                "type": "delta",
                "text": final_message,
            }

            break

        streamed_parts: list[str] = []
        streamed_response = None

        # Crucial difference from the previous implementation:
        # tools=[] here. Ollama only streams the final natural answer,
        # never the tool-selection turn.
        for stream_event in stream_method(
            model=selected_model,
            messages=messages,
            tools=[],
        ):
            event_type = (
                stream_event.get(
                    "type"
                )
            )

            if event_type == "delta":
                text = str(
                    stream_event.get(
                        "text"
                    )
                    or ""
                )

                if not text:
                    continue

                streamed_parts.append(
                    text
                )

                yield {
                    "type": "delta",
                    "text": text,
                }

                continue

            if event_type == "result":
                streamed_response = (
                    stream_event.get(
                        "response"
                    )
                )

        final_message = (
            "".join(
                streamed_parts
            ).strip()
        )

        if (
            not final_message
            and streamed_response
            is not None
        ):
            final_message = (
                streamed_response
                .text
                .strip()
            )

        if not final_message:
            # Last-resort fallback to the non-streaming selection
            # answer so the user never receives an empty bubble.
            final_message = (
                provider_response
                .text
                .strip()
                or "No response was generated."
            )

            yield {
                "type": "delta",
                "text": final_message,
            }

        break

    else:
        final_message = (
            "The assistant reached the maximum "
            "number of tool operations."
        )

        yield {
            "type": "delta",
            "text": final_message,
        }

    response = ChatResponse(
        conversationId=(
            request.conversationId
            or str(
                uuid.uuid4()
            )
        ),
        message=final_message,
        model=selected_model,
        toolsUsed=tool_history,
        sources=chat_sources,
    )

    yield {
        "type": "done",
        "response": response,
    }