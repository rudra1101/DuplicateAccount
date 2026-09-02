from __future__ import annotations

from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.ai.authorization import (
    get_rudrix_actor,
    has_rudrix_permission,
)
from app.ai.tools.action_tools import SearchRemediationItemsTool
from app.ai.tools.base import BaseAITool
from app.ai.tools.review_tools import GetReviewStatisticsTool
from app.services.duplicate_group_feedback_service import (
    save_duplicate_group_candidate_decision,
)
from app.services.remediation_service import (
    list_decision_history,
    update_remediation_status,
)
from app.services.service_desk_service import sync_ticket_by_id


class RudrixReviewOperationsTool(BaseAITool):
    """Read review statistics or submit an explicit duplicate decision."""

    # Reuse the existing routed tool name so the fast intent router continues
    # selecting this capability for review/duplicate conversations.
    name = "get_review_statistics"
    description = (
        "Work with the CURRENT IdentityAI review queue. Use operation STATS for "
        "review counts. Use DECIDE only when the user explicitly instructs Rudrix "
        "to mark a known candidate as DUPLICATE, NOT_DUPLICATE, or UNCERTAIN. "
        "DECIDE changes review state and requires duplicate.review. Never guess a "
        "candidate ID or decision; locate the candidate with duplicate-group tools first."
    )
    parameters = {
        "type": "object",
        "properties": {
            # Preserve the original review-statistics arguments so existing
            # conversations/tests remain compatible.
            "integration": {"type": ["string", "null"]},
            "application": {"type": ["string", "null"]},
            "operation": {
                "type": ["string", "null"],
                "enum": ["STATS", "DECIDE", None],
            },
            "candidate_id": {"type": ["integer", "null"], "minimum": 1},
            "decision": {
                "type": ["string", "null"],
                "enum": ["DUPLICATE", "NOT_DUPLICATE", "UNCERTAIN", None],
            },
            "comment": {"type": ["string", "null"]},
        },
        "required": ["integration", "application"],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        operation = str(arguments.get("operation") or "STATS").strip().upper()

        if operation == "STATS":
            return GetReviewStatisticsTool().execute(
                db=db,
                arguments={
                    "integration": arguments.get("integration"),
                    "application": arguments.get("application"),
                },
            )

        if operation != "DECIDE":
            raise ValueError("Unsupported review operation.")

        if not has_rudrix_permission("duplicate.review"):
            raise PermissionError(
                "You do not have permission to submit review decisions. "
                "The required permission is duplicate.review."
            )

        candidate_id = arguments.get("candidate_id")
        decision = str(arguments.get("decision") or "").strip().upper()
        if candidate_id is None:
            raise ValueError("candidate_id is required for a review decision.")
        if decision not in {"DUPLICATE", "NOT_DUPLICATE", "UNCERTAIN"}:
            raise ValueError("A valid review decision is required.")

        actor = get_rudrix_actor()
        user_comment = str(arguments.get("comment") or "").strip()
        audit_comment = "Submitted via Rudrix."
        if user_comment:
            audit_comment += f" {user_comment}"

        result = save_duplicate_group_candidate_decision(
            db=db,
            candidate_id=int(candidate_id),
            decision=decision,
            comment=audit_comment,
            reviewer_name=actor,
        )

        application = str(arguments.get("application") or "").strip()
        route = "/review"
        if application:
            route = f"/review/{quote(application, safe='')}"

        return {
            "message": (
                f"Marked candidate **{int(candidate_id)}** as **{decision}**. "
                f"[Open Review Queue]({route})"
            ),
            "candidateId": int(candidate_id),
            "decision": decision,
            "reviewer": actor,
            "result": result,
            "clientAction": {
                "type": "NAVIGATE",
                "label": "Open Review Queue",
                "route": route,
                "autoExecute": False,
            },
        }


class RudrixRemediationOperationsTool(BaseAITool):
    """Search remediation work and perform safe operational follow-up actions."""

    name = "search_remediation_items"
    description = (
        "Search CURRENT remediation work, inspect decision history, sync an existing "
        "Service Desk ticket, or ignore a remediation item. SEARCH is read-only and "
        "uses remediation.view. HISTORY requires remediation.history.view. "
        "SYNC_TICKET and IGNORE require remediation.manage. IGNORE sends the pair back "
        "to review and must only be used when the user explicitly asks for it."
    )
    parameters = {
        "type": "object",
        "properties": {
            # Preserve the original search schema and add optional workflow actions.
            "search": {"type": ["string", "null"]},
            "application": {"type": ["string", "null"]},
            "status": {"type": ["string", "null"]},
            "minimum_confidence": {
                "type": ["number", "null"],
                "minimum": 0,
                "maximum": 100,
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            "operation": {
                "type": ["string", "null"],
                "enum": ["SEARCH", "HISTORY", "SYNC_TICKET", "IGNORE", None],
            },
            "item_id": {"type": ["integer", "null"], "minimum": 1},
            "comment": {"type": ["string", "null"]},
        },
        "required": [
            "search",
            "application",
            "status",
            "minimum_confidence",
            "limit",
        ],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        operation = str(arguments.get("operation") or "SEARCH").strip().upper()

        if operation == "SEARCH":
            return SearchRemediationItemsTool().execute(
                db=db,
                arguments={
                    "search": arguments.get("search"),
                    "application": arguments.get("application"),
                    "status": arguments.get("status"),
                    "minimum_confidence": arguments.get("minimum_confidence"),
                    "limit": min(int(arguments.get("limit") or 10), 20),
                },
            )

        if operation == "HISTORY":
            if not has_rudrix_permission("remediation.history.view"):
                raise PermissionError(
                    "You do not have permission to view remediation decision history. "
                    "The required permission is remediation.history.view."
                )
            limit = max(1, min(int(arguments.get("limit") or 20), 50))
            items = list_decision_history(db, limit=limit)
            return {
                "count": len(items),
                "items": items,
                "message": f"Loaded {len(items)} recent decision-history item(s).",
            }

        if not has_rudrix_permission("remediation.manage"):
            raise PermissionError(
                "You do not have permission to manage remediation items. "
                "The required permission is remediation.manage."
            )

        item_id = arguments.get("item_id")
        if item_id is None:
            raise ValueError("item_id is required for this remediation action.")
        actor = get_rudrix_actor()

        if operation == "SYNC_TICKET":
            result = sync_ticket_by_id(db, int(item_id))
            status = result.get("ticketStatus") or result.get("status") or "updated"
            return {
                **result,
                "message": (
                    f"Synced remediation item **{int(item_id)}**. "
                    f"Ticket status is **{status}**. "
                    "[Open Remediation](/remediation)"
                ),
                "clientAction": {
                    "type": "NAVIGATE",
                    "label": "Open Remediation",
                    "route": "/remediation",
                    "autoExecute": False,
                },
            }

        if operation == "IGNORE":
            comment = str(arguments.get("comment") or "").strip()
            action_comment = "Ignored via Rudrix and returned to Review Queue."
            if comment:
                action_comment += f" {comment}"
            result = update_remediation_status(
                db,
                item_id=int(item_id),
                status="IGNORED",
                action_comment=action_comment,
                actioned_by=actor,
            )
            return {
                **result,
                "message": (
                    f"Ignored remediation item **{int(item_id)}**. The duplicate pair "
                    "is eligible for review again. [Open Review Queue](/review)"
                ),
                "clientAction": {
                    "type": "NAVIGATE",
                    "label": "Open Review Queue",
                    "route": "/review",
                    "autoExecute": False,
                },
            }

        raise ValueError("Unsupported remediation operation.")
