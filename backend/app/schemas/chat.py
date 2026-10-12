from __future__ import annotations

import re
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


_EXPLICIT_ACCOUNT_LOOKUP = re.compile(
    r"^(?:find|locate|lookup|look\s+up|search(?:\s+for)?)\s+"
    r"(?:the\s+)?(?:account|accout)\b",
    flags=re.IGNORECASE,
)

_REFERENTIAL_LOOKUP_TERMS = re.compile(
    r"\b(?:same|that|this|those|these|it|them)\b",
    flags=re.IGNORECASE,
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

    @field_validator("message")
    @classmethod
    def normalize_account_lookup_typos(cls, value: str) -> str:
        """Repair a few high-confidence lookup typos before tool routing.

        Rudrix's fast router deliberately relies on simple intent terms. A user
        typing ``ind account`` (missing the leading ``f``) should not make an
        account search fall through to unrelated tools from chat history.
        Preserve all other wording and only repair unambiguous lookup prefixes.
        """
        text = str(value or "")
        text = re.sub(
            r"^(\s*)ind(?=\s+(?:the\s+)?(?:account|accout)\b)",
            r"\1find",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^(\s*find\s+(?:the\s+)?)accout\b",
            r"\1account",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        return text

    @model_validator(mode="after")
    def isolate_explicit_account_lookup(self):
        """Keep a concrete account lookup from inheriting unrelated tool intent.

        The fast router also considers recent history so normal follow-ups work.
        For an explicit named account lookup that is not referential, stale
        mentions of remediation, duplicates, reports, etc. can expose unrelated
        tools to the local model. A fresh concrete lookup does not need that
        history, so isolate it. Referential requests such as "find that account"
        retain history because they depend on previous context.
        """
        message = " ".join(self.message.strip().split())
        if (
            _EXPLICIT_ACCOUNT_LOOKUP.match(message)
            and not _REFERENTIAL_LOOKUP_TERMS.search(message)
        ):
            self.history = []
        return self


class ToolInvocationResponse(
    BaseModel
):
    name: str

    arguments: dict[
        str,
        Any,
    ]

    result: Any


def _structured_tool_message(
    tools_used: list[ToolInvocationResponse],
) -> str | None:
    """Render records only when they are the latest successful operation.

    IdentityAI search/list capabilities return current records through an ``items``
    collection. If the latest successful operation is such a read, those records are
    authoritative and cannot be replaced by unrelated model prose. If a later
    successful report, ticket, review, navigation, or other action has completed,
    that newer operation supersedes the earlier read and the normal final response
    is preserved.
    """

    for invocation in reversed(tools_used):
        result = invocation.result if isinstance(invocation.result, dict) else {}
        if not result.get("success"):
            continue

        data = result.get("data")
        if not isinstance(data, dict):
            return None

        items = data.get("items")
        if not isinstance(items, list):
            return None

        message = str(data.get("message") or "").strip()
        if not items:
            return message or "No matching current records were found."

        lines = [message] if message else [f"Found {len(items)} matching record(s)."]

        for item in items[:20]:
            if not isinstance(item, dict):
                continue

            label = (
                item.get("displayName")
                or item.get("name")
                or item.get("username")
                or item.get("nativeIdentity")
                or item.get("email")
                or item.get("employeeId")
                or item.get("sourceAccountId")
                or item.get("id")
                or "Record"
            )

            details: list[str] = []
            for key, display in (
                ("application", "application"),
                ("integrationName", "source"),
                ("connectorType", "connector"),
                ("employeeId", "employee ID"),
                ("orphanType", "orphan type"),
                ("orphanStatus", "orphan status"),
                ("reason", "reason"),
                ("status", "status"),
                ("confidence", "confidence"),
                ("decision", "decision"),
                ("state", "state"),
            ):
                value = item.get(key)
                if value not in (None, ""):
                    details.append(f"{display}: {value}")

            suffix = f" — {', '.join(details)}" if details else ""
            lines.append(f"- **{label}**{suffix}")

        if len(items) > 20:
            lines.append(f"- …and {len(items) - 20} more matching record(s).")

        return "\n".join(lines)

    return None


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

    @model_validator(mode="after")
    def prefer_authoritative_structured_tool_result(self):
        grounded_message = _structured_tool_message(self.toolsUsed)
        if grounded_message:
            self.message = grounded_message
        return self


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
