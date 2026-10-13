from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.authorization import get_rudrix_actor
from app.ai.tools.base import BaseAITool
from app.services.orphan_account_service import list_orphan_accounts
from app.services.orphan_remediation_service import create_orphan_ticket


VALID_ACTIONS = {"DISABLE", "DELETE"}


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _account_label(account: dict[str, Any]) -> str:
    return str(
        account.get("displayName")
        or account.get("username")
        or account.get("nativeIdentity")
        or account.get("employeeId")
        or account.get("sourceAccountId")
        or "orphan account"
    )


def _candidate(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "sourceAccountId": account.get("sourceAccountId"),
        "displayName": account.get("displayName"),
        "username": account.get("username"),
        "email": account.get("email"),
        "employeeId": account.get("employeeId"),
        "nativeIdentity": account.get("nativeIdentity"),
        "application": account.get("application"),
        "integrationName": account.get("integrationName"),
        "orphanType": account.get("orphanType"),
        "orphanStatus": account.get("orphanStatus"),
    }


class CreateOrphanRemediationTicketTool(BaseAITool):
    name = "create_orphan_remediation_ticket"
    description = (
        "Prepare or create a real Service Desk remediation ticket for one CURRENT orphan "
        "account. Use only when the user explicitly asks to create/open/raise a remediation "
        "ticket for an orphan account. Resolve the target by grounded source_account_id or a "
        "human reference such as display name, username, email, employee ID, or native identity. "
        "An orphan has one target account, so only the remediation action is required: DISABLE "
        "or DELETE. If the action or account is missing/ambiguous, return the required input "
        "instead of guessing or creating a ticket."
    )
    parameters = {
        "type": "object",
        "properties": {
            "reference": {
                "type": ["string", "null"],
                "description": (
                    "Human orphan-account reference, optionally embedded in the user's sentence."
                ),
            },
            "source_account_id": {
                "type": ["integer", "null"],
                "description": "Grounded source-account ID when already known from prior results.",
            },
            "action": {
                "type": ["string", "null"],
                "enum": ["DISABLE", "DELETE", None],
                "description": "Requested remediation action. Never guess this value.",
            },
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        reference = _clean(arguments.get("reference"))
        raw_source_account_id = arguments.get("source_account_id")
        source_account_id: int | None = None
        if raw_source_account_id is not None:
            try:
                source_account_id = int(raw_source_account_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("source_account_id must be numeric.") from exc

        if source_account_id is None and not reference:
            return {
                "resultType": "orphan_remediation_ticket",
                "created": False,
                "requiresInput": True,
                "missingFields": ["account"],
                "message": (
                    "Please identify the current orphan account before I prepare a real "
                    "Service Desk remediation ticket."
                ),
            }

        items = list_orphan_accounts(
            db,
            source_account_id=source_account_id,
            search=reference if source_account_id is None else None,
            limit=20,
        )

        if not items:
            target = reference or str(source_account_id)
            return {
                "resultType": "orphan_remediation_ticket",
                "created": False,
                "found": False,
                "reference": target,
                "message": f"No current orphan account matched **{target}**.",
            }

        if len(items) > 1:
            candidates = [_candidate(item) for item in items]
            lines = [
                "Multiple current orphan accounts matched that reference. Choose one before "
                "I prepare a remediation ticket:"
            ]
            for candidate in candidates[:10]:
                label = _account_label(candidate)
                details = [
                    str(value)
                    for value in (
                        candidate.get("employeeId"),
                        candidate.get("username"),
                        candidate.get("application"),
                    )
                    if value not in (None, "")
                ]
                suffix = f" — {', '.join(details)}" if details else ""
                lines.append(f"- **{label}**{suffix}")
            return {
                "resultType": "orphan_remediation_ticket",
                "created": False,
                "requiresSelection": True,
                "candidates": candidates,
                "message": "\n".join(lines),
            }

        account = items[0]
        resolved_source_account_id = int(account["sourceAccountId"])
        action = str(arguments.get("action") or "").strip().upper()
        if action not in VALID_ACTIONS:
            label = _account_label(account)
            return {
                "resultType": "orphan_remediation_ticket",
                "created": False,
                "requiresInput": True,
                "missingFields": ["action"],
                "sourceAccountId": resolved_source_account_id,
                "account": _candidate(account),
                "message": (
                    f"I found **{label}** as the current orphan account. Before I create a "
                    "real Service Desk ticket, tell me whether the account should be "
                    "**DISABLE** or **DELETE**."
                ),
            }

        result = create_orphan_ticket(
            db,
            source_account_id=resolved_source_account_id,
            action=action,
            requested_by=get_rudrix_actor(),
        )

        ticket_id = result.get("ticketId") or "created ticket"
        label = _account_label(result)
        ticket_url = result.get("ticketUrl")
        message = (
            f"Created Service Desk ticket **{ticket_id}** to **{action.lower()}** orphan "
            f"account **{label}**."
        )
        if ticket_url:
            message += f" [Open ticket]({ticket_url})"

        response = {
            **result,
            "resultType": "orphan_remediation_ticket",
            "message": message,
        }
        if ticket_url:
            response["clientAction"] = {
                "type": "OPEN_EXTERNAL",
                "label": f"Open ticket {ticket_id}",
                "url": ticket_url,
                "autoExecute": False,
            }
        return response
