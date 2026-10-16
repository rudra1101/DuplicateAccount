from __future__ import annotations

import re
from datetime import datetime
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


def _format_execution_timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return raw

    month_day = parsed.strftime("%b %d, %Y").replace(" 0", " ")
    hour = parsed.strftime("%I").lstrip("0") or "0"
    clock = f"{hour}:{parsed.strftime('%M:%S %p')}"
    offset = parsed.strftime("%z")
    if offset:
        offset = f"UTC{offset[:3]}:{offset[3:]}"
        return f"{month_day} at {clock} ({offset})"
    return f"{month_day} at {clock}"


def _execution_subject(execution: dict[str, Any]) -> str:
    integration_name = str(execution.get("integrationName") or "Integration").strip()
    execution_id = execution.get("executionId") or execution.get("id")
    if execution_id is None:
        return integration_name
    return f"{integration_name} execution {execution_id}"


def _execution_response_message(
    data: dict[str, Any],
    user_message: str | None,
) -> str | None:
    """Render a concise authoritative execution answer for the user's exact question.

    Capability selection and grounding happen earlier in the agent. This formatter does
    not route tools or infer new facts; it only selects which already-persisted execution
    fields to present. Broad result/detail questions retain the canonical full summary.
    """

    default_message = str(data.get("message") or "").strip()
    execution = data.get("execution")
    if not isinstance(execution, dict):
        return default_message or None

    request = " ".join(str(user_message or "").casefold().split())
    if not request:
        return default_message or None

    subject = _execution_subject(execution)
    status = str(execution.get("status") or "UNKNOWN").upper()
    error_message = str(execution.get("errorMessage") or "").strip()

    if (
        ("why" in request and ("fail" in request or "error" in request))
        or "failure reason" in request
        or "error reason" in request
    ):
        if status == "FAILED":
            if error_message:
                return f"{subject} failed because: {error_message}"
            return f"{subject} failed, but no failure reason was recorded."
        if status == "COMPLETED":
            return f"{subject} did not fail; it completed successfully."
        return f"{subject} has status {status}; no failure reason is recorded."

    if (
        "when" in request
        or "finish time" in request
        or "completion time" in request
        or "completed at" in request
        or "finished at" in request
    ):
        completed_at = _format_execution_timestamp(execution.get("completedAt"))
        if completed_at:
            return f"{subject} finished on {completed_at}."
        started_at = _format_execution_timestamp(execution.get("startedAt"))
        if status == "RUNNING" and started_at:
            return f"{subject} is still running; it started on {started_at}."
        return f"No completion time is recorded yet for {subject}."

    if "duplicate" in request:
        duplicate_groups = execution.get("duplicateGroups")
        duplicate_accounts = execution.get("duplicateAccounts")
        if duplicate_groups is None and duplicate_accounts is None:
            return f"No duplicate counts are recorded for {subject}."

        groups = int(duplicate_groups or 0)
        accounts = int(duplicate_accounts or 0)
        yes_no = request.startswith(("did ", "does ", "has ", "have ", "is ", "are "))

        if "group" in request and "account" not in request:
            answer = f"{groups} duplicate group{'s' if groups != 1 else ''} were found."
        elif "account" in request and "group" not in request:
            answer = f"{accounts} duplicate account{'s' if accounts != 1 else ''} were found."
        else:
            answer = (
                f"{accounts} duplicate account{'s' if accounts != 1 else ''} "
                f"across {groups} duplicate group{'s' if groups != 1 else ''} were found."
            )

        if yes_no:
            return ("Yes. " if accounts > 0 or groups > 0 else "No. ") + answer
        return answer

    if "scan" in request and "account" in request:
        accounts_scanned = execution.get("accountsScanned")
        if accounts_scanned is not None:
            count = int(accounts_scanned)
            return f"{count} account{'s' if count != 1 else ''} were scanned in {subject}."

    change_fields = (
        ("created", "accountsCreated", "created"),
        ("updated", "accountsUpdated", "updated"),
        ("unchanged", "accountsUnchanged", "unchanged"),
        ("deleted", "accountsDeleted", "deleted"),
    )
    requested_changes = [
        (key, label)
        for term, key, label in change_fields
        if term in request
    ]
    if requested_changes:
        parts = []
        for key, label in requested_changes:
            value = execution.get(key)
            if value is not None:
                parts.append(f"{label}: {value}")
        if parts:
            return f"Account changes for {subject} — {', '.join(parts)}."

    if "status" in request:
        return f"{subject} status is {status}."

    if "complete" in request or "completed" in request:
        if status == "COMPLETED":
            return f"Yes. {subject} completed successfully."
        if status == "RUNNING":
            return f"Not yet. {subject} is still running."
        if status == "FAILED":
            suffix = f" Reason: {error_message}" if error_message else ""
            return f"No. {subject} failed.{suffix}"
        return f"{subject} has status {status}."

    return default_message or None


def execution_tool_message(
    tools_used: list[ToolInvocationResponse],
    *,
    user_message: str | None = None,
) -> str | None:
    """Return the latest authoritative execution answer for stream-time rendering."""

    for invocation in reversed(tools_used):
        result = invocation.result if isinstance(invocation.result, dict) else {}
        if not result.get("success"):
            continue
        data = result.get("data")
        if not isinstance(data, dict):
            continue
        if data.get("resultType") != "integration_execution":
            continue
        return _execution_response_message(data, user_message)
    return None


def _structured_tool_message(
    tools_used: list[ToolInvocationResponse],
    *,
    user_message: str | None = None,
) -> str | None:
    """Prefer the latest successful authoritative IdentityAI result.

    Current-record capabilities expose ``items`` and are rendered deterministically
    so model prose cannot replace live rows. Structured workflow result families can
    provide a server-generated authoritative message when they must preserve exact
    persisted evidence, execution facts, or a real side-effect result. Download/report
    capabilities expose a structured ``DOWNLOAD_REPORT`` client action plus a server-
    generated message carrying the authenticated download URL. Other successful actions
    continue to use normal model synthesis.
    """

    for invocation in reversed(tools_used):
        result = invocation.result if isinstance(invocation.result, dict) else {}
        if not result.get("success"):
            continue

        data = result.get("data")
        if not isinstance(data, dict):
            return None

        message = str(data.get("message") or "").strip()
        result_type = data.get("resultType")
        if result_type == "integration_execution":
            return _execution_response_message(data, user_message)

        if result_type in {
            "orphan_explanation",
            "orphan_remediation_ticket",
        } and message:
            return message

        client_action = data.get("clientAction")
        if (
            isinstance(client_action, dict)
            and client_action.get("type") == "DOWNLOAD_REPORT"
            and message
        ):
            return message

        items = data.get("items")
        if not isinstance(items, list):
            return None

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

    requestMessage: str | None = Field(
        default=None,
        exclude=True,
    )

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
        grounded_message = _structured_tool_message(
            self.toolsUsed,
            user_message=self.requestMessage,
        )
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
