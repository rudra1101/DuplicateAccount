from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.workflow_action_tools import (
    RudrixRemediationOperationsTool as _BaseRudrixRemediationOperationsTool,
)
from app.services.remediation_service import list_remediation_items


_NULL_LIKE = {"", "null", "none", "nil", "n/a", "undefined"}
_VALID_OPERATIONS = {"SEARCH", "HISTORY", "SYNC_TICKET", "IGNORE"}
_ACTIONABLE_STATUSES = {"PENDING_ACTION", "TICKET_OPEN"}
_VALID_STATUSES = {
    *_ACTIONABLE_STATUSES,
    "ACTIONED",
    "IGNORED",
    "FAILED",
    "ACTIONABLE",
    "NEEDS_TICKET",
    "ALL",
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
    """Normalize local-model arguments and apply remediation-queue defaults.

    The Remediation page defaults to PENDING_ACTION, which is also the set eligible
    for ticket creation. Generic list requests therefore default to PENDING_ACTION.
    ACTIONABLE is reserved for the broader in-progress scope of PENDING_ACTION plus
    TICKET_OPEN. NEEDS_TICKET is an explicit alias for pending items without a ticket.
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
    if operation == "SEARCH" and status is None:
        status = "PENDING_ACTION"
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


def _search_remediation_items(
    *,
    db: Session,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    status_scope = str(arguments.get("status") or "PENDING_ACTION").strip().upper()
    application = _optional_text(arguments.get("application"))
    minimum_confidence = arguments.get("minimum_confidence")
    limit = _bounded_int(arguments.get("limit"), default=10, minimum=1, maximum=50)
    search = (_optional_text(arguments.get("search")) or "").lower()

    if status_scope == "NEEDS_TICKET":
        service_status = "PENDING_ACTION"
    elif status_scope in {"ACTIONABLE", "ALL"}:
        service_status = None
    else:
        service_status = status_scope

    items = list_remediation_items(
        db,
        status=service_status,
        application=application,
        min_confidence=(
            float(minimum_confidence)
            if minimum_confidence is not None
            else None
        ),
    )

    if status_scope == "ACTIONABLE":
        items = [
            item
            for item in items
            if str(item.get("status") or "").upper() in _ACTIONABLE_STATUSES
        ]
    elif status_scope == "NEEDS_TICKET":
        items = [
            item
            for item in items
            if str(item.get("status") or "").upper() == "PENDING_ACTION"
            and not item.get("ticketId")
        ]

    if search:
        filtered: list[dict[str, Any]] = []
        for item in items:
            searchable = " ".join(
                [
                    str(item.get("account1Key") or ""),
                    str(item.get("account2Key") or ""),
                    json.dumps(item.get("account1") or {}, default=str),
                    json.dumps(item.get("account2") or {}, default=str),
                ]
            ).lower()
            if search in searchable:
                filtered.append(item)
        items = filtered

    total_matching = len(items)
    results: list[dict[str, Any]] = []
    for item in items[:limit]:
        account1 = item.get("account1") or {}
        account2 = item.get("account2") or {}
        results.append(
            {
                "remediationItemId": item.get("id"),
                "integrationId": item.get("integrationId"),
                "integrationName": item.get("integrationName"),
                "application": item.get("application"),
                "confidence": item.get("confidence"),
                "status": item.get("status"),
                "ticketId": item.get("ticketId"),
                "ticketStatus": item.get("ticketStatus"),
                "needsTicket": (
                    str(item.get("status") or "").upper() == "PENDING_ACTION"
                    and not item.get("ticketId")
                ),
                "account1": {
                    "key": item.get("account1Key"),
                    "username": account1.get("username"),
                    "email": account1.get("email"),
                },
                "account2": {
                    "key": item.get("account2Key"),
                    "username": account2.get("username"),
                    "email": account2.get("email"),
                },
            }
        )

    return {
        "count": len(results),
        "returnedItems": len(results),
        "totalMatching": total_matching,
        "statusScope": status_scope,
        "actionableStatuses": sorted(_ACTIONABLE_STATUSES),
        "items": results,
    }


class RudrixRemediationOperationsTool(_BaseRudrixRemediationOperationsTool):
    """Remediation workflow tool aligned with the Remediation page semantics."""

    description = (
        "Search CURRENT remediation work, inspect decision history, sync an existing "
        "Service Desk ticket, or ignore a remediation item. PENDING_ACTION means the "
        "item still needs a remediation ticket/action and matches the default Remediation "
        "queue. ACTIONABLE means PENDING_ACTION plus TICKET_OPEN. NEEDS_TICKET means "
        "PENDING_ACTION with no existing ticket. Use ALL only when the user explicitly "
        "asks for every remediation state. HISTORY requires remediation.history.view. "
        "SYNC_TICKET and IGNORE require remediation.manage. Never infer which account "
        "in a duplicate pair should be disabled or deleted."
    )

    # Extend the inherited schema with the two virtual search scopes understood by
    # this wrapper. Keeping all existing fields preserves backward compatibility.
    parameters = {
        **_BaseRudrixRemediationOperationsTool.parameters,
        "properties": {
            **_BaseRudrixRemediationOperationsTool.parameters["properties"],
            "status": {
                "type": ["string", "null"],
                "enum": [
                    "PENDING_ACTION",
                    "TICKET_OPEN",
                    "ACTIONED",
                    "IGNORED",
                    "FAILED",
                    "ACTIONABLE",
                    "NEEDS_TICKET",
                    "ALL",
                    None,
                ],
            },
        },
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        normalized = normalize_remediation_arguments(arguments)
        if normalized["operation"] == "SEARCH":
            return _search_remediation_items(db=db, arguments=normalized)
        return super().execute(db=db, arguments=normalized)
