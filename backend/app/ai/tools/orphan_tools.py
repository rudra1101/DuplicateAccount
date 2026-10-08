from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.services.orphan_account_service import ORPHAN_TYPES, list_orphan_accounts


class SearchOrphanAccountsTool(BaseAITool):
    name = "search_orphan_accounts"
    description = (
        "Search CURRENT orphan accounts using live IdentityAI orphan state. Use for requests "
        "such as 'show orphan accounts from Active Directory', 'show terminated identity "
        "orphans', 'why did correlation fail', or orphan-account filtering. Results include "
        "persisted correlation reason, policy, attempts, and matched identity when available."
    )
    parameters = {
        "type": "object",
        "properties": {
            "integration": {"type": ["string", "null"]},
            "application": {"type": ["string", "null"]},
            "orphan_type": {
                "type": ["string", "null"],
                "enum": [*sorted(ORPHAN_TYPES), None],
            },
            "status": {"type": ["string", "null"]},
            "search": {"type": ["string", "null"]},
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
        orphan_type = str(arguments.get("orphan_type") or "").strip().upper() or None
        status = str(arguments.get("status") or "").strip().upper() or None
        search = str(arguments.get("search") or "").strip() or None
        reason = str(arguments.get("reason") or "").strip() or None
        date_from = str(arguments.get("date_from") or "").strip() or None
        date_to = str(arguments.get("date_to") or "").strip() or None
        limit = max(1, min(int(arguments.get("limit") or 20), 50))

        last_days = arguments.get("last_days")
        if last_days is not None and not date_from:
            days = max(1, min(int(last_days), 3650))
            date_from = (datetime.now(UTC).date() - timedelta(days=days)).isoformat()

        items = list_orphan_accounts(
            db,
            integration_name=integration,
            application=application,
            orphan_type=orphan_type,
            status=status,
            search=search,
            reason=reason,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )

        integration_ids = {item.get("integrationId") for item in items if item.get("integrationId")}
        report_filters: dict[str, Any] = {}
        if len(integration_ids) == 1:
            report_filters["integrationId"] = next(iter(integration_ids))
        if application:
            report_filters["application"] = application
        if orphan_type:
            # The shared report API already exposes `status`; for orphan reports this
            # value is interpreted as orphan type when it matches a known type.
            report_filters["status"] = orphan_type
        elif status:
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
