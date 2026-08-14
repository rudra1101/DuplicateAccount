import json
import uuid
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
                "role": message.role,
                "content": message.content,
            }
        )

    messages.append(
        {
            "role": "user",
            "content": request.message,
        }
    )

    return messages


def extract_text_tool_calls(
    content: str,
    allowed_tools: set[str],
) -> list[dict[str, Any]]:
    """
    Fallback parser for local models that emit tool calls
    as plain JSON text instead of native tool_calls.

    Supported examples:

    {
        "name": "get_dashboard_summary",
        "parameters": {
            "period": "daily"
        }
    }

    {
        "name": "search_knowledge_base",
        "arguments": {
            "query": "duplicate review policy"
        }
    }
    """

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
                    "name": name,
                    "arguments": arguments,
                }
            )

    return tool_calls


def normalize_tool_arguments(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    Defensive normalization for common local-model
    schema mistakes.

    Handles:
    - numeric values sent as strings
    - "null" / "None" sent as strings
    - knowledge search limit exceeding maximum
    - invalid semantic similarity values
    """

    normalized = dict(
        arguments
    )

    # -------------------------------------------------
    # Confidence breakdown
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Knowledge / RAG search
    # -------------------------------------------------

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

                except (
                    TypeError,
                    ValueError,
                ):
                    normalized[
                        "document_id"
                    ] = None

        elif document_id is None:
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

            except (
                TypeError,
                ValueError,
            ):
                normalized[
                    "document_id"
                ] = None

    return normalized


def compact_dashboard_applications(
    applications: Any,
) -> list[dict[str, Any]]:
    """
    Keep only useful application-level dashboard metrics.

    This prevents a local model from receiving unnecessary
    payload fields when it only needs to synthesize an answer.
    """

    if not isinstance(
        applications,
        list,
    ):
        return []

    compacted: list[
        dict[str, Any]
    ] = []

    for application in applications:
        if not isinstance(
            application,
            dict,
        ):
            continue

        compacted.append(
            {
                "application":
                    application.get(
                        "application"
                    ),

                "duplicateGroups":
                    application.get(
                        "duplicateGroups"
                    ),

                "duplicateAccounts":
                    application.get(
                        "duplicateAccounts"
                    ),

                "highestConfidence":
                    application.get(
                        "highestConfidence"
                    ),

                "highConfidenceGroups":
                    application.get(
                        "highConfidenceGroups"
                    ),
            }
        )

    return compacted


def compact_tool_result_for_model(
    *,
    tool_name: str,
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a smaller tool result to the LLM while keeping the
    complete original tool result in toolsUsed.

    This is especially important for local 8B models because
    very large scan/trend payloads can distract the model from
    the actual metric the user asked for.

    toolsUsed:
        receives the complete result.

    LLM:
        receives a compact result focused on relevant fields.
    """

    if not tool_result.get(
        "success"
    ):
        return tool_result

    data = tool_result.get(
        "data"
    )

    if not isinstance(
        data,
        dict,
    ):
        return tool_result

    # -------------------------------------------------
    # Dashboard
    #
    # Do NOT send scans/trend history unless the
    # current tool is specifically a history tool.
    # -------------------------------------------------

    if tool_name == (
        "get_dashboard_summary"
    ):
        return {
            "success": True,
            "data": {
                "hasData":
                    data.get(
                        "hasData"
                    ),

                "period":
                    data.get(
                        "period"
                    ),

                "summary":
                    data.get(
                        "summary",
                        {},
                    ),

                "applications":
                    compact_dashboard_applications(
                        data.get(
                            "applications",
                            [],
                        )
                    ),
            },
        }

    # -------------------------------------------------
    # Confidence breakdown
    # -------------------------------------------------

    if tool_name == (
        "get_confidence_breakdown"
    ):
        return {
            "success": True,
            "data": {
                "totalMatchingAccounts":
                    data.get(
                        "totalMatchingAccounts"
                    ),

                "applicationCount":
                    data.get(
                        "applicationCount"
                    ),

                "applications":
                    data.get(
                        "applications",
                        [],
                    ),
            },
        }

    # -------------------------------------------------
    # Knowledge / RAG
    #
    # Keep retrieved source content because the model
    # needs it to answer grounded policy/document questions.
    # -------------------------------------------------

    if tool_name == (
        "search_knowledge_base"
    ):
        return {
            "success": True,
            "data": {
                "found":
                    data.get(
                        "found"
                    ),

                "query":
                    data.get(
                        "query"
                    ),

                "resultCount":
                    data.get(
                        "resultCount"
                    ),

                "documentId":
                    data.get(
                        "documentId"
                    ),

                "sources":
                    data.get(
                        "sources",
                        [],
                    ),

                "message":
                    data.get(
                        "message"
                    ),
            },
        }

    # -------------------------------------------------
    # Knowledge document listing
    # -------------------------------------------------

    if tool_name == (
        "list_knowledge_documents"
    ):
        return {
            "success": True,
            "data": {
                "documentCount":
                    data.get(
                        "documentCount"
                    ),

                "documents":
                    data.get(
                        "documents",
                        [],
                    ),
            },
        }

    # -------------------------------------------------
    # Duplicate group search
    #
    # Keep authoritative totals and returned groups.
    # -------------------------------------------------

    if tool_name == (
        "search_duplicate_groups"
    ):
        return {
            "success": True,
            "data": {
                "totalMatchingGroups":
                    data.get(
                        "totalMatchingGroups"
                    ),

                "totalMatchingDuplicateAccounts":
                    data.get(
                        "totalMatchingDuplicateAccounts"
                    ),

                "returnedGroups":
                    data.get(
                        "returnedGroups"
                    ),

                "groups":
                    data.get(
                        "groups",
                        [],
                    ),
            },
        }

    # -------------------------------------------------
    # Other tools are already reasonably scoped.
    # -------------------------------------------------

    return tool_result


def extract_chat_sources(
    *,
    tool_name: str,
    tool_result: dict[str, Any],
) -> list[ChatSource]:
    """
    Extract structured knowledge-document sources from
    successful search_knowledge_base results.
    """

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
                documentId=(
                    document_id
                ),
                documentName=(
                    str(
                        document_name
                    )
                ),
                pageNumber=(
                    page_number
                ),
            )
        )

    return sources


def run_identity_agent(
    *,
    db: Session,
    request: ChatRequest,
) -> ChatResponse:
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

    for _ in range(
        settings.max_tool_iterations
    ):
        provider_response = (
            provider.chat(
                model=selected_model,
                messages=messages,
                tools=registry.definitions(),
            )
        )

        messages.append(
            provider_response.assistant_message
        )

        tool_calls = list(
            provider_response.tool_calls
            or []
        )

        # -------------------------------------------------
        # Fallback:
        #
        # Some Ollama/local models print function calls as
        # normal JSON text instead of native tool_calls.
        # -------------------------------------------------

        if not tool_calls:
            allowed_tools = {
                definition["name"]
                for definition
                in registry.definitions()
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

        # -------------------------------------------------
        # No tool call means the model has produced the
        # final user-facing response.
        # -------------------------------------------------

        if not tool_calls:
            final_message = (
                provider_response.text.strip()
                or "No response was generated."
            )

            break

        # -------------------------------------------------
        # Execute all requested tools.
        # -------------------------------------------------

        for tool_call in tool_calls:

            # Native provider tool call object.
            if not isinstance(
                tool_call,
                dict,
            ):
                tool_name = (
                    tool_call.name
                )

                tool_arguments = (
                    tool_call.arguments
                )

            # Fallback textual tool-call dictionary.
            else:
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

            # -------------------------------------------------
            # Execute tool.
            # -------------------------------------------------

            try:
                result = (
                    registry.execute(
                        name=tool_name,
                        db=db,
                        arguments=(
                            tool_arguments
                        ),
                    )
                )

                tool_result = {
                    "success": True,
                    "data": result,
                }

            except Exception as exc:
                tool_result = {
                    "success": False,
                    "error": str(
                        exc
                    ),
                }

            # -------------------------------------------------
            # Keep FULL result for debugging/API response.
            # -------------------------------------------------

            tool_history.append(
                ToolInvocationResponse(
                    name=tool_name,
                    arguments=(
                        tool_arguments
                    ),
                    result=(
                        tool_result
                    ),
                )
            )

            # -------------------------------------------------
            # Extract structured RAG sources.
            # -------------------------------------------------

            discovered_sources = (
                extract_chat_sources(
                    tool_name=tool_name,
                    tool_result=tool_result,
                )
            )

            for source in discovered_sources:
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

            # -------------------------------------------------
            # IMPORTANT:
            #
            # Send compact result to the LLM instead of the
            # full raw tool payload.
            #
            # This prevents dashboard scan/trend arrays from
            # distracting llama3.1:8b.
            # -------------------------------------------------

            model_tool_result = (
                compact_tool_result_for_model(
                    tool_name=tool_name,
                    tool_result=tool_result,
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_name": (
                        tool_name
                    ),
                    "content": json.dumps(
                        model_tool_result,
                        default=str,
                    ),
                }
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
        message=final_message,
        model=selected_model,
        toolsUsed=tool_history,
        sources=chat_sources,
    )