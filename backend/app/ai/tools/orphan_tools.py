from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.account_investigation_tools import InvestigateAccountsTool
from app.ai.tools.base import BaseAITool
from app.services.orphan_account_service import ORPHAN_TYPES, list_orphan_accounts


def _normalized_source_reference(value: str | None) -> str:
    return " ".join(
        str(value or "").strip().replace("_", " ").replace("-", " ").casefold().split()
    )


def _normalize_orphan_filters(
    orphan_type: str | None,
    status: str | None,
) -> tuple[str | None, str | None]:
    normalized_type = str(orphan_type or "").strip().upper() or None
    normalized_status = str(status or "").strip().upper() or None
    if normalized_status in ORPHAN_TYPES:
        if normalized_type is None:
            normalized_type = normalized_status
        normalized_status = None
    return normalized_type, normalized_status


def _normalized_account_reference(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _items_support_account_reference(reference: str, items: list[dict[str, Any]]) -> bool:
    """Return true only when a recovered value actually names an account.

    A small local model can place a person's display name in ``reason``, ``integration``,
    or ``application``. Recovery is only accepted when the value contains a concrete
    account identifier from the returned rows. This prevents genuine source names or
    correlation-reason text from being silently reinterpreted as account references.
    """

    normalized_reference = _normalized_account_reference(reference)
    if not normalized_reference:
        return False

    for item in items:
        if not isinstance(item, dict):
            continue
        for key in (
            "displayName",
            "username",
            "email",
            "employeeId",
            "nativeIdentity",
        ):
            normalized_value = _normalized_account_reference(item.get(key))
            if not normalized_value:
                continue
            if normalized_value in normalized_reference:
                return True
            # Permit a short concrete reference such as APP04 only when it resolved
            # uniquely; do not use this looser direction for multi-row results.
            if (
                len(items) == 1
                and len(normalized_reference) >= 4
                and normalized_reference in normalized_value
            ):
                return True
    return False


class SearchOrphanAccountsTool(BaseAITool):
    name = "search_orphan_accounts"
    description = (
        "Search CURRENT orphan accounts using live IdentityAI orphan state. The source can be "
        "identified by configured integration name, connector type, or account application. "
        "Use for requests such as 'show orphan accounts from Active Directory', 'show "
        "terminated identity orphans', 'why did correlation fail', or orphan-account filtering. "
        "Results include persisted correlation reason, policy, attempts, and matched identity."
    )
    parameters = {
        "type": "object",
        "properties": {
            "integration": {
                "type": ["string", "null"],
                "description": "Optional source/integration reference such as Active Directory.",
            },
            "application": {"type": ["string", "null"]},
            "orphan_type": {
                "type": ["string", "null"],
                "enum": [*sorted(ORPHAN_TYPES), None],
            },
            "status": {"type": ["string", "null"]},
            "search": {
                "type": ["string", "null"],
                "description": (
                    "Optional account reference or text. Prefer the display name, username, "
                    "email, employee ID, or native identity when the user asks about one orphan."
                ),
            },
            "reason": {"type": ["string", "null"]},
            "date_from": {"type": ["string", "null"]},
            "date_to": {"type": ["string", "null"]},
            "last_days": {"type": ["integer", "null"], "minimum": 1, "maximum": 3650},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        integration = str(arguments.get("integration") or "").strip() or None
        application = str(arguments.get("application") or "").strip() or None

        # Small models sometimes put the same human source reference into both fields.
        # Treat that as one source reference instead of AND-ing two independent filters.
        if (
            integration
            and application
            and _normalized_source_reference(integration)
            == _normalized_source_reference(application)
        ):
            application = None

        # Keep orphan classification and workflow status semantically separate even
        # when a small model places a known orphan type in the generic status field.
        orphan_type, status = _normalize_orphan_filters(
            arguments.get("orphan_type"),
            arguments.get("status"),
        )
        search = str(arguments.get("search") or "").strip() or None
        reason = str(arguments.get("reason") or "").strip() or None
        date_from = str(arguments.get("date_from") or "").strip() or None
        date_to = str(arguments.get("date_to") or "").strip() or None
        limit = max(1, min(int(arguments.get("limit") or 20), 50))

        last_days = arguments.get("last_days")
        if last_days is not None and not date_from:
            days = max(1, min(int(last_days), 3650))
            date_from = (datetime.now(UTC).date() - timedelta(days=days)).isoformat()

        def find_items(
            *,
            effective_integration: str | None,
            effective_application: str | None,
            effective_search: str | None,
            effective_reason: str | None,
        ) -> list[dict[str, Any]]:
            return list_orphan_accounts(
                db,
                integration_name=effective_integration,
                application=effective_application,
                orphan_type=orphan_type,
                status=status,
                search=effective_search,
                reason=effective_reason,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
            )

        items = find_items(
            effective_integration=integration,
            effective_application=application,
            effective_search=search,
            effective_reason=reason,
        )

        if not items:
            # Local models occasionally bind a named account to the wrong free-text
            # argument (most commonly ``reason``). Retry only reversible bindings and
            # accept them only when the candidate is proven by an account identifier
            # in the recovered live rows. Structured type/status/date filters remain.
            recovery_attempts: list[
                tuple[str, str | None, str | None]
            ] = []

            if search and reason:
                recovery_attempts.append((search, integration, application))
            if reason:
                recovery_attempts.append((reason, integration, application))
            if integration:
                recovery_attempts.append((integration, None, application))
            if application:
                recovery_attempts.append((application, integration, None))

            seen_attempts: set[tuple[str, str | None, str | None]] = set()
            for reference, recovered_integration, recovered_application in recovery_attempts:
                attempt_key = (
                    _normalized_account_reference(reference),
                    recovered_integration,
                    recovered_application,
                )
                if attempt_key in seen_attempts:
                    continue
                seen_attempts.add(attempt_key)

                recovered_items = find_items(
                    effective_integration=recovered_integration,
                    effective_application=recovered_application,
                    effective_search=reference,
                    effective_reason=None,
                )
                if not recovered_items or not _items_support_account_reference(
                    reference,
                    recovered_items,
                ):
                    continue

                items = recovered_items
                integration = recovered_integration
                application = recovered_application
                search = reference
                reason = None
                break

        integration_ids = {item.get("integrationId") for item in items if item.get("integrationId")}
        report_filters: dict[str, Any] = {}
        if len(integration_ids) == 1:
            report_filters["integrationId"] = next(iter(integration_ids))
        if application:
            report_filters["application"] = application
        if orphan_type:
            report_filters["orphanType"] = orphan_type
        if status:
            report_filters["status"] = status
        if reason:
            report_filters["search"] = reason
        elif search:
            report_filters["search"] = search
        if date_from:
            report_filters["dateFrom"] = date_from
        if date_to:
            report_filters["dateTo"] = date_to

        return {
            "count": len(items),
            "items": items,
            "reportType": "orphan_accounts",
            "reportFilters": report_filters,
            "message": (
                f"Found {len(items)} current orphan account(s)."
                if items
                else "No current orphan accounts matched those filters."
            ),
        }


class GroundedAccountInvestigationTool(InvestigateAccountsTool):
    """Preserve fast account lookup while allowing broad orphan-list requests."""

    description = (
        "Find a specific current account OR list/filter current orphan accounts. For a broad "
        "orphan request, set orphan_only=true, keep query empty, and put the human source "
        "reference in integration. For a specific orphan account, set orphan_only=true and put "
        "only the username/email/employee ID/display name in query. Results use persisted "
        "correlation evidence; never invent a correlation reason."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": ["string", "null"]},
            "application": {"type": ["string", "null"]},
            "integration": {"type": ["string", "null"]},
            "orphan_only": {"type": ["boolean", "null"]},
            "orphan_type": {
                "type": ["string", "null"],
                "enum": [*sorted(ORPHAN_TYPES), None],
            },
            "status": {"type": ["string", "null"]},
            "reason": {"type": ["string", "null"]},
            "last_days": {"type": ["integer", "null"], "minimum": 1, "maximum": 3650},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
        },
        "required": [],
        "additionalProperties": False,
    }

    @staticmethod
    def _reference_from_orphan_sentence(raw_query: str) -> str | None:
        employee_id = re.search(r"\b[A-Za-z][A-Za-z0-9_-]*\d{3,}\b", raw_query)
        if employee_id:
            return employee_id.group(0)

        email = re.search(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b", raw_query)
        if email:
            return email.group(0).strip(".,;:!?")

        return None

    @staticmethod
    def _integration_from_orphan_sentence(raw_query: str) -> str | None:
        match = re.search(
            r"\b(?:from|in)\s+(.+?)\s*$",
            raw_query,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        value = match.group(1).strip(" .?!,;:")
        return value or None

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        raw_query = str(arguments.get("query") or "").strip()
        query_lower = raw_query.casefold()
        contains_orphan_language = "orphan" in query_lower or "uncorrelated" in query_lower
        generic_orphan_query = query_lower.strip(" .?!") in {
            "orphan",
            "orphans",
            "orphan account",
            "orphan accounts",
            "all orphan accounts",
            "current orphan accounts",
        }
        orphan_mode = bool(arguments.get("orphan_only")) or generic_orphan_query or not raw_query
        orphan_mode = orphan_mode or contains_orphan_language or any(
            arguments.get(key) not in (None, "")
            for key in ("orphan_type", "reason", "last_days")
        )

        if not orphan_mode:
            return super().execute(db=db, arguments=arguments)

        integration = arguments.get("integration")
        if not integration and contains_orphan_language:
            integration = self._integration_from_orphan_sentence(raw_query)

        search: str | None
        if generic_orphan_query:
            search = None
        elif contains_orphan_language:
            search = self._reference_from_orphan_sentence(raw_query) or raw_query
        else:
            search = raw_query or None

        result = SearchOrphanAccountsTool().execute(
            db=db,
            arguments={
                "integration": integration,
                "application": arguments.get("application"),
                "orphan_type": arguments.get("orphan_type"),
                "status": arguments.get("status"),
                "search": search,
                "reason": arguments.get("reason"),
                "last_days": arguments.get("last_days"),
                "limit": arguments.get("limit") or 20,
            },
        )
        return {**result, "queryMode": "orphan_search"}
