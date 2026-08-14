from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    Field,
)


class ChatHistoryMessage(
    BaseModel
):
    role: str
    content: str


class ChatRequest(
    BaseModel
):
    message: str

    conversationId: str | None = None

    history: list[
        ChatHistoryMessage
    ] = Field(
        default_factory=list
    )

    useReasoningModel: bool = False


class ToolInvocationResponse(
    BaseModel
):
    name: str

    arguments: dict[
        str,
        Any,
    ]

    result: Any


class ChatSource(
    BaseModel
):
    documentId: int

    documentName: str

    pageNumber: int | None = None


class ChatResponse(
    BaseModel
):
    conversationId: str

    message: str

    model: str

    toolsUsed: list[
        ToolInvocationResponse
    ] = Field(
        default_factory=list
    )

    sources: list[
        ChatSource
    ] = Field(
        default_factory=list
    )


class ChatConversationSummary(
    BaseModel
):
    id: str

    title: str

    createdAt: str | None = None

    updatedAt: str | None = None


class StoredChatMessage(
    BaseModel
):
    id: int

    conversationId: str

    role: str

    content: str

    model: str | None = None

    sources: list[
        ChatSource
    ] = Field(
        default_factory=list
    )

    createdAt: str | None = None


class ChatConversationDetails(
    BaseModel
):
    id: str

    title: str

    createdAt: str | None = None

    updatedAt: str | None = None

    messages: list[
        StoredChatMessage
    ] = Field(
        default_factory=list
    )