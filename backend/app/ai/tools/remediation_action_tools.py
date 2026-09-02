from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.workflow_action_tools import (
    RudrixRemediationOperationsTool as _BaseRudrixRemediationOperationsTool,
)


_NULL_LIKE = {"", "null", "none", "nil", "n/a", "undefined"}
_VALID_OPERATIONS = {"SEARCH", "HISTORY", "SYNC_TICKET", "IGNORE"}
_VALID_STATUSES = {
    "PENDING_ACTION",
    "TICKET_OPEN",
    "ACTIONED",
    "IGNORED",
    "FAILED",
}


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _NULL_LIKE:
        return None
    return text


def _optional_float(value: Any) -> float | None:
    text = _optional_text(value)
    if text is None:
        return None
    try:
        return max(0.0, min(float(text), 100.0))
    except (TypeError, ValueError):
        return None


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    text = _optional_text(value)
    if text is None:
        return default
    try:
        parsed = int(float(text))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def normalize_remediation_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Normalize common local-model argument variants before execution.

    Ollama can occasionally emit the strings ``"null"``/``"None"`` for optional
    tool fields. Passing those values through makes the remediation service treat
    them as real status/application/search values and can fail an otherwise valid
    read-only request such as "give me the list of remediation items".
    """

    normalized = dict(arguments or {})

    operation = (_optional_text(normalized.get("operation")) or "SEARCH").upper()
    if operation not in _VALID_OPERATIONS:
        operation = "SEARCH"
    normalized["operation"] = operation

    normalized["search"] = _optional_text(normalized.get("search"))
    normalized["application"] = _optional_text(normalized.get("application"))

    status = _optional_text(normalized.get("status"))
    if status is not None:
        status = status.upper()
        if status not in _VALID_STATUSES:
            status = None
    normalized["status"] = status

    normalized["minimum_confidence"] = _optional_float(
        normalized.get("minimum_confidence")
    )
    normalized["limit"] = _bounded_int(
        normalized.get("limit"),
        default=10,
        minimum=1,
        maximum=50,
    )

    item_id_text = _optional_text(normalized.get("item_id"))
    if item_id_text is None:
        normalized["item_id"] = None
    else:
        try:
            item_id = int(float(item_id_text))
            normalized["item_id"] = item_id if item_id > 0 else None
        except (TypeError, ValueError):
            normalized["item_id"] = None

    normalized["comment"] = _optional_text(normalized.get("comment"))
    return normalized


class RudrixRemediationOperationsTool(_BaseRudrixRemediationOperationsTool):
    """Remediation workflow tool with defensive local-model argument handling."""

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        return super().execute(
            db=db,
            arguments=normalize_remediation_arguments(arguments),
        )
