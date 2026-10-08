from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.orphan_account_service import ORPHAN_TYPES, list_orphan_accounts
from app.services import report_service


ORPHAN_REPORT_TYPE = "orphan_accounts"


def _orphan_rows(db: Session, filters: dict[str, Any]) -> list[dict[str, Any]]:
    raw_status = str(filters.get("status") or "").strip().upper()
    orphan_type = raw_status if raw_status in ORPHAN_TYPES else None
    orphan_status = raw_status if raw_status and raw_status not in ORPHAN_TYPES else None

    items = list_orphan_accounts(
        db,
        integration_id=(
            int(filters["integrationId"])
            if filters.get("integrationId") is not None
            else None
        ),
        application=str(filters.get("application") or "").strip() or None,
        orphan_type=orphan_type,
        status=orphan_status,
        search=str(filters.get("search") or "").strip() or None,
        date_from=str(filters.get("dateFrom") or "").strip() or None,
        date_to=str(filters.get("dateTo") or "").strip() or None,
    )

    return [
        {
            "orphanStateId": item.get("orphanStateId"),
            "sourceAccountId": item.get("sourceAccountId"),
            "integration": item.get("integrationName"),
            "application": item.get("application"),
            "username": item.get("username"),
            "displayName": item.get("displayName"),
            "email": item.get("email"),
            "employeeId": item.get("employeeId"),
            "nativeIdentity": item.get("nativeIdentity"),
            "accountStatus": item.get("accountStatus"),
            "orphanType": item.get("orphanType"),
            "orphanStatus": item.get("orphanStatus"),
            "reason": item.get("reason"),
            "correlationMethod": item.get("correlationMethod"),
            "policyName": item.get("policyName"),
            "strategy": item.get("strategy"),
            "firstDetectedAt": item.get("firstDetectedAt"),
            "lastDetectedAt": item.get("lastDetectedAt"),
        }
        for item in items
    ]


def register_orphan_report() -> None:
    """Idempotently extend the shared report catalog with orphan-account data."""

    if not any(
        str(item.get("type") or "") == ORPHAN_REPORT_TYPE
        for item in report_service.REPORT_CATALOG
    ):
        report_service.REPORT_CATALOG.append(
            {
                "type": ORPHAN_REPORT_TYPE,
                "name": "Orphan Accounts",
                "description": (
                    "Current orphan accounts with persisted correlation evidence and reason."
                ),
                "filters": [
                    "integrationId",
                    "application",
                    "status",
                    "search",
                    "dateFrom",
                    "dateTo",
                ],
            }
        )

    report_service.ROW_BUILDERS[ORPHAN_REPORT_TYPE] = _orphan_rows
