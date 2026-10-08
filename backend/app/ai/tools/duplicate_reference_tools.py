from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.tools.account_resolution_tools import GroundedSearchDuplicateGroupsTool
from app.ai.tools.review_tools import GetDuplicateGroupDetailsTool
from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _candidate_reference_values(candidate: DuplicateCandidateRecord) -> list[str]:
    account = candidate.account_data if isinstance(candidate.account_data, dict) else {}
    return [
        _text(candidate.username),
        _text(account.get("username")),
        _text(account.get("displayName") or account.get("display_name")),
        _text(account.get("email")),
        _text(account.get("employeeId") or account.get("employee_id")),
        _text(account.get("nativeIdentity") or account.get("native_identity")),
    ]


class CompleteDuplicateReferenceSearchTool(GroundedSearchDuplicateGroupsTool):
    """Search both sides of a duplicate pair using human-facing account fields.

    The legacy duplicate-group query searches all primary-account fields, but only
    candidate usernames. This compatibility layer fills that gap so employee IDs,
    emails, display names, and native identities work whether the referenced account
    is the primary or candidate side of the current duplicate pair.
    """

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        result = super().execute(db=db, arguments=arguments)
        if not isinstance(result, dict) or result.get("found"):
            return result

        search = _text(arguments.get("search"))
        if not search:
            return result

        scan_ids = [
            int(scan_id)
            for scan_id in (result.get("scanIds") or [])
            if str(scan_id).isdigit()
        ]
        if not scan_ids:
            return result

        minimum_confidence = float(result.get("minimumConfidence") or 0)
        application = _text(result.get("application"))
        needle = search.casefold()

        statement = (
            select(DuplicateCandidateRecord, DuplicateGroupRecord)
            .join(
                DuplicateGroupRecord,
                DuplicateGroupRecord.id == DuplicateCandidateRecord.group_id,
            )
            .where(
                DuplicateGroupRecord.scan_id.in_(scan_ids),
                DuplicateGroupRecord.highest_confidence >= minimum_confidence,
            )
        )
        if application:
            statement = statement.where(DuplicateGroupRecord.application.ilike(application))

        matching_group_ids: list[int] = []
        group_duplicate_counts: dict[int, int] = {}
        for candidate, group in db.execute(statement).all():
            values = _candidate_reference_values(candidate)
            if not any(needle in value.casefold() for value in values if value):
                continue
            group_id = int(group.id)
            if group_id not in matching_group_ids:
                matching_group_ids.append(group_id)
                group_duplicate_counts[group_id] = int(group.duplicate_count or 0)

        if not matching_group_ids:
            return result

        try:
            limit = max(1, min(int(arguments.get("limit") or 20), 50))
        except (TypeError, ValueError):
            limit = 20

        details_tool = GetDuplicateGroupDetailsTool()
        groups: list[dict[str, Any]] = []
        for group_id in matching_group_ids[:limit]:
            details = details_tool.execute(db=db, arguments={"group_id": group_id})
            if not isinstance(details, dict) or not details.get("found"):
                continue
            groups.append(
                {
                    "groupId": details.get("groupId"),
                    "scanId": details.get("scanId"),
                    "application": details.get("application"),
                    "primaryUsername": details.get("primaryUsername"),
                    "primaryDisplayName": (
                        (details.get("primaryAccount") or {}).get("displayName")
                    ),
                    "duplicateAccounts": int(details.get("duplicateAccounts") or 0),
                    "highestConfidence": float(details.get("highestConfidence") or 0),
                    "primaryAccount": details.get("primaryAccount"),
                    "candidates": details.get("candidates") or [],
                }
            )

        total_groups = len(matching_group_ids)
        return {
            **result,
            "found": total_groups > 0,
            "totalMatchingGroups": total_groups,
            "totalMatchingDuplicateAccounts": sum(group_duplicate_counts.values()),
            "returnedGroups": len(groups),
            "groups": groups,
        }
