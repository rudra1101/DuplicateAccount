from __future__ import annotations

import json
from typing import Any

from app.ai.agent_core.models import AgentState
from app.db_models.chat_conversation import ChatConversationRecord
from app.schemas.chat import ChatHistoryMessage, ChatUIContext


_STATE_CONTEXT_MARKER = "RUDRIX_GROUNDED_STATE"
_UI_CONTEXT_MARKER = "RUDRIX_UI_CONTEXT"


def load_agent_state(
    conversation: ChatConversationRecord | Any | None,
) -> AgentState:
    """Load durable grounded state, failing safely for legacy/corrupt rows."""
    raw = getattr(conversation, "agent_state", None) if conversation is not None else None
    if not isinstance(raw, dict):
        return AgentState()

    try:
        return AgentState.model_validate(raw)
    except Exception:
        return AgentState()


def save_agent_state(
    conversation: ChatConversationRecord | Any,
    state: AgentState,
) -> None:
    conversation.agent_state = state.compact()


def load_ui_context(
    conversation: ChatConversationRecord | Any | None,
) -> ChatUIContext | None:
    raw = getattr(conversation, "ui_context", None) if conversation is not None else None
    if not isinstance(raw, dict):
        return None

    try:
        return ChatUIContext.model_validate(raw)
    except Exception:
        return None


def save_ui_context(
    conversation: ChatConversationRecord | Any,
    context: ChatUIContext | None,
) -> None:
    if context is not None:
        conversation.ui_context = context.model_dump(exclude_none=True)


def agent_context_messages(
    state: AgentState,
    ui_context: ChatUIContext | None,
) -> list[ChatHistoryMessage]:
    """Create hidden system context consumed by the existing agent runtime.

    Grounded state is authoritative only because it was produced by successful
    server-side tools and persisted by the backend. UI context is explicitly a
    navigation hint and must never replace live tool data.
    """
    messages: list[ChatHistoryMessage] = []

    if state.compact():
        messages.append(
            ChatHistoryMessage(
                role="system",
                content=(
                    f"{_STATE_CONTEXT_MARKER}: "
                    + json.dumps(state.compact(), default=str, separators=(",", ":"))
                    + "\nThis state contains grounded IdentityAI entities from prior successful tool "
                    "calls. Reuse exact entity IDs for references such as it, this account, "
                    "the duplicate, that candidate, or the remediation item. Never invent or "
                    "replace these IDs from conversational prose."
                ),
            )
        )

    if ui_context is not None:
        messages.append(
            ChatHistoryMessage(
                role="system",
                content=(
                    f"{_UI_CONTEXT_MARKER}: "
                    + json.dumps(
                        ui_context.model_dump(exclude_none=True),
                        default=str,
                        separators=(",", ":"),
                    )
                    + "\nThis is the user's current IdentityAI UI/navigation context only. "
                    "Use it to understand words such as here, this page, this screen, or the "
                    "selected record. Verify all live IAM facts and actions with authorized tools."
                ),
            )
        )

    return messages
