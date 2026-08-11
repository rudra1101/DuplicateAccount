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


def run_identity_agent(
    *,
    db: Session,
    request: ChatRequest,
) -> ChatResponse:
    settings = get_ai_settings()

    provider = AIProviderFactory.create(
        settings
    )

    registry = create_ai_tool_registry()

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

    final_message = ""

    for _ in range(
        settings.max_tool_iterations
    ):
        provider_response = provider.chat(
            model=selected_model,
            messages=messages,
            tools=registry.definitions(),
        )

        messages.append(
            provider_response.assistant_message
        )

        if not provider_response.tool_calls:
            final_message = (
                provider_response.text.strip()
                or "No response was generated."
            )
            break

        for tool_call in (
            provider_response.tool_calls
        ):
            try:
                result = registry.execute(
                    name=tool_call.name,
                    db=db,
                    arguments=(
                        tool_call.arguments
                    ),
                )

                tool_result = {
                    "success": True,
                    "data": result,
                }

            except Exception as exc:
                tool_result = {
                    "success": False,
                    "error": str(exc),
                }

            tool_history.append(
                ToolInvocationResponse(
                    name=tool_call.name,
                    arguments=(
                        tool_call.arguments
                    ),
                    result=tool_result,
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_name": (
                        tool_call.name
                    ),
                    "content": json.dumps(
                        tool_result,
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
            or str(uuid.uuid4())
        ),
        message=final_message,
        model=selected_model,
        toolsUsed=tool_history,
    )