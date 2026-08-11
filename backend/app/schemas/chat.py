from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
)


ChatRole = Literal[
    "user",
    "assistant",
]


class ChatMessage(BaseModel):
    role: ChatRole

    content: str = Field(
        min_length=1,
        max_length=20_000,
    )


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=20_000,
    )

    conversationId: str | None = Field(
        default=None,
        max_length=100,
    )

    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=30,
    )

    useReasoningModel: bool = False


class ToolInvocationResponse(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: Any


class ChatResponse(BaseModel):
    conversationId: str
    message: str
    model: str
    toolsUsed: list[ToolInvocationResponse]