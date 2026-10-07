from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.action_tools import CreateRemediationTicketTool
from app.ai.tools.review_tools import (
    GetDuplicateGroupDetailsTool,
    SearchDuplicateGroupsTool,
)
from app.ai.tools.workflow_action_tools import RudrixReviewOperationsTool
from app.services.remediation_service import list_remediation_items


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _candidate_matches_reference(candidate: dict[str, Any], reference: str) -> bool:
    needle = _text(reference).casefold()
    if not needle:
        return False

    account = candidate.get("account") or {}
    values = [
        candidate.get("username"),
        account.get("username"),
        account.get("displayName"),
        account.get("display_name"),
        account.get("email"),
        account.get("employeeId"),
        account.get("employee_id"),
        account.get("nativeIdentity"),
        account.get("native_identity"),
    ]
    return any(_text(value).casefold() == needle for value in values if value is not None)


def _remediation_search_text(item: dict[str, Any]) -> str:
    return " ".join(
        [
            str(item.get("account1Key") or ""),
            str(item.get("account2Key") or ""),
            json.dumps(item.get("account1") or {}, default=str),
            json.dumps(item.get("account2") or {}, default=str),
        ]
    ).casefold()


class GroundedSearchDuplicateGroupsTool(SearchDuplicateGroupsTool):
    """Duplicate search that returns the real candidate rows for every group."""

    description = (
        "Search CURRENT duplicate groups using a username, display name, email, "
        "employee ID, or other account reference. Use this for questions such as "
        "'is W00003 a duplicate?' or 'does this account have duplicates?'. The "
        "result includes the persisted primary account and actual candidate IDs, "
        "usernames, confidence, reasoning, and review state. Never infer a candidate "
        "that is not present in this result."
    )

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        result = super().execute(db=db, arguments=arguments)
        groups = result.get("groups") if isinstance(result, dict) else None
        if not isinstance(groups, list) or not groups:
            return result

        enriched: list[dict[str, Any]] = []
        details_tool = GetDuplicateGroupDetailsTool()
        for group in groups:
            group_id = group.get("groupId") if isinstance(group, dict) else None
            if not isinstance(group_id, int):
                enriched.append(group)
                continue

            details = details_tool.execute(db=db, arguments={"group_id": group_id})
            if not isinstance(details, dict) or not details.get("found"):
                enriched.append(group)
                continue

            enriched.append(
                {
                    **group,
                    "primaryAccount": details.get("primaryAccount"),
                    "candidates": details.get("candidates") or [],
                }
            )

        return {**result, "groups": enriched}


class GroundedDuplicateGroupDetailsTool(GetDuplicateGroupDetailsTool):
    """Accept either a real group ID or an account reference without coercion."""

    parameters = {
        "type": "object",
        "properties": {
            "group_id": {
                "type": ["integer", "string"],
                "description": (
                    "Duplicate group ID. If the user supplied an employee ID, username, "
                    "email, or display name instead, pass that value unchanged and it "
                    "will be resolved through current duplicate data."
                ),
            },
        },
        "required": ["group_id"],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        raw = _text(arguments.get("group_id"))
        if raw.isdigit():
            return super().execute(db=db, arguments={"group_id": int(raw)})

        if not raw:
            raise ValueError("A duplicate group ID or account reference is required.")

        return GroundedSearchDuplicateGroupsTool().execute(
            db=db,
            arguments={
                "integration": None,
                "application": None,
                "minimum_confidence": 0,
                "search": raw,
                "limit": 20,
            },
        )


class GroundedReviewOperationsTool(RudrixReviewOperationsTool):
    """Resolve human-facing account references before review decisions."""

    parameters = {
        **RudrixReviewOperationsTool.parameters,
        "properties": {
            **RudrixReviewOperationsTool.parameters["properties"],
            "candidate_id": {
                "type": ["integer", "string", "null"],
                "description": (
                    "Candidate ID when known. If the user supplied an employee ID, "
                    "username, email, or display name instead, pass it unchanged."
                ),
            },
            "account_reference": {
                "type": ["string", "null"],
                "description": (
                    "Optional human-facing employee ID, username, email, or display name "
                    "used to locate the candidate before a review decision."
                ),
            },
        },
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        operation = _text(arguments.get("operation") or "STATS").upper()
        if operation != "DECIDE":
            return super().execute(db=db, arguments=arguments)

        raw_candidate = arguments.get("candidate_id")
        if isinstance(raw_candidate, int) and raw_candidate > 0:
            return super().execute(db=db, arguments=arguments)

        candidate_text = _text(raw_candidate)
        if candidate_text.isdigit():
            resolved = dict(arguments)
            resolved["candidate_id"] = int(candidate_text)
            return super().execute(db=db, arguments=resolved)

        reference = _text(arguments.get("account_reference")) or candidate_text
        if not reference:
            return {
                "changed": False,
                "requiresSelection": True,
                "message": (
                    "I need the duplicate candidate or an account reference before I can "
                    "confirm a duplicate."
                ),
            }

        search_result = GroundedSearchDuplicateGroupsTool().execute(
            db=db,
            arguments={
                "integration": arguments.get("integration"),
                "application": arguments.get("application"),
                "minimum_confidence": 0,
                "search": reference,
                "limit": 20,
            },
        )
        groups = search_result.get("groups") or []
        if not groups:
            return {
                "changed": False,
                "found": False,
                "reference": reference,
                "message": f"No current duplicate candidate matched `{reference}`.",
            }

        all_candidates: list[dict[str, Any]] = []
        direct_candidates: list[dict[str, Any]] = []
        for group in groups:
            group_id = group.get("groupId")
            for candidate in group.get("candidates") or []:
                entry = {
                    **candidate,
                    "groupId": group_id,
                    "application": group.get("application"),
                    "primaryUsername": group.get("primaryUsername"),
                }
                all_candidates.append(entry)
                if _candidate_matches_reference(candidate, reference):
                    direct_candidates.append(entry)

        candidates = direct_candidates or all_candidates
        if len(candidates) != 1:
            return {
                "changed": False,
                "requiresSelection": True,
                "reference": reference,
                "count": len(candidates),
                "candidates": candidates,
                "message": (
                    f"I found {len(candidates)} duplicate candidates related to "
                    f"`{reference}`. Please choose the candidate username or candidate ID "
                    "you want to confirm."
                ),
            }

        chosen = candidates[0]
        resolved = dict(arguments)
        resolved["candidate_id"] = int(chosen["id"])
        resolved.pop("account_reference", None)
        return super().execute(db=db, arguments=resolved)


class GroundedCreateRemediationTicketTool(CreateRemediationTicketTool):
    """Resolve account references to remediation items before any side effect."""

    parameters = {
        "type": "object",
        "properties": {
            "remediation_item_id": {
                "type": ["integer", "string", "null"],
                "description": (
                    "Remediation item ID when known. If the user gives an employee ID, "
                    "username, email, or display name instead, pass it unchanged."
                ),
            },
            "account_reference": {
                "type": ["string", "null"],
                "description": (
                    "Human-facing employee ID, username, email, or display name used to "
                    "locate the remediation item when its internal ID is not known."
                ),
            },
            "target": {
                "type": ["string", "null"],
                "enum": ["ACCOUNT_1", "ACCOUNT_2", None],
                "description": "Which account in the duplicate pair should be remediated.",
            },
            "action": {
                "type": ["string", "null"],
                "enum": ["DISABLE", "DELETE", None],
                "description": "Requested remediation action.",
            },
        },
        "required": [
            "remediation_item_id",
            "account_reference",
            "target",
            "action",
        ],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        raw_item = arguments.get("remediation_item_id")
        if isinstance(raw_item, int) and raw_item > 0:
            if arguments.get("target") and arguments.get("action"):
                return super().execute(db=db, arguments=arguments)
            return {
                "created": False,
                "remediationItemId": raw_item,
                "requiresInput": True,
                "message": (
                    f"Remediation item **{raw_item}** is identified, but I still need the "
                    "target account and whether it should be DISABLE or DELETE before "
                    "creating a ticket."
                ),
            }

        item_text = _text(raw_item)
        if item_text.isdigit():
            resolved = dict(arguments)
            resolved["remediation_item_id"] = int(item_text)
            return self.execute(db=db, arguments=resolved)

        reference = _text(arguments.get("account_reference")) or item_text
        if not reference:
            return {
                "created": False,
                "requiresInput": True,
                "message": (
                    "I need a remediation item ID or an account reference before I can "
                    "prepare the ticket."
                ),
            }

        items = list_remediation_items(db, status="PENDING_ACTION")
        needle = reference.casefold()
        matches = [item for item in items if needle in _remediation_search_text(item)]

        if not matches:
            return {
                "created": False,
                "found": False,
                "reference": reference,
                "message": (
                    f"No pending remediation item matched `{reference}`. If the duplicate "
                    "has not been confirmed yet, confirm the correct candidate first."
                ),
            }

        if len(matches) > 1:
            choices = [
                {
                    "remediationItemId": item.get("id"),
                    "application": item.get("application"),
                    "confidence": item.get("confidence"),
                    "account1Key": item.get("account1Key"),
                    "account2Key": item.get("account2Key"),
                }
                for item in matches[:20]
            ]
            return {
                "created": False,
                "requiresSelection": True,
                "reference": reference,
                "count": len(matches),
                "items": choices,
                "message": (
                    f"I found {len(matches)} pending remediation items related to "
                    f"`{reference}`. Please choose the remediation item or duplicate pair."
                ),
            }

        item = matches[0]
        item_id = int(item["id"])
        target = _text(arguments.get("target")).upper()
        action = _text(arguments.get("action")).upper()
        if target not in {"ACCOUNT_1", "ACCOUNT_2"} or action not in {"DISABLE", "DELETE"}:
            account1 = item.get("account1") or {}
            account2 = item.get("account2") or {}
            return {
                "created": False,
                "requiresInput": True,
                "reference": reference,
                "remediationItemId": item_id,
                "application": item.get("application"),
                "account1": {
                    "key": item.get("account1Key"),
                    "username": account1.get("username"),
                    "email": account1.get("email"),
                    "employeeId": account1.get("employeeId") or account1.get("employee_id"),
                },
                "account2": {
                    "key": item.get("account2Key"),
                    "username": account2.get("username"),
                    "email": account2.get("email"),
                    "employeeId": account2.get("employeeId") or account2.get("employee_id"),
                },
                "message": (
                    f"I found remediation item **{item_id}** for `{reference}`. Before I "
                    "create a real Service Desk ticket, tell me which account to remediate "
                    "(ACCOUNT_1 or ACCOUNT_2) and whether to DISABLE or DELETE it."
                ),
            }

        resolved = dict(arguments)
        resolved["remediation_item_id"] = item_id
        resolved["target"] = target
        resolved["action"] = action
        resolved.pop("account_reference", None)
        return super().execute(db=db, arguments=resolved)
