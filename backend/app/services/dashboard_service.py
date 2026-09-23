from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.integration import (
    IntegrationRecord,
)
from app.db_models.scan import (
    ScanRecord,
)
from app.services.review_visibility_service import (
    get_visible_duplicate_groups,
    get_visible_review_summary,
)


VALID_PERIODS = {
    "daily",
    "weekly",
    "monthly",
    "yearly",
}

DASHBOARD_TOP_APPLICATIONS = 10
DASHBOARD_RECENT_SCANS = 6
DASHBOARD_TREND_POINTS = 60


def normalize_application_name(
    value: str | None,
) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def get_latest_completed_scans_by_integration(
    db: Session,
) -> list[ScanRecord]:
    """
    Return only the latest completed scan for each integration.

    Legacy scans with integration_id = NULL are ignored when
    integration-linked scans exist.
    """

    scans = list(
        db.scalars(
            select(ScanRecord)
            .where(
                ScanRecord.status
                == "COMPLETED"
            )
            .order_by(
                ScanRecord.created_at.desc(),
                ScanRecord.id.desc(),
            )
        ).all()
    )

    linked_scans = [
        scan
        for scan in scans
        if scan.integration_id
        is not None
    ]

    latest_by_integration: dict[
        int,
        ScanRecord,
    ] = {}

    for scan in linked_scans:
        integration_id = int(
            scan.integration_id
        )

        if (
            integration_id
            not in latest_by_integration
        ):
            latest_by_integration[
                integration_id
            ] = scan

    if latest_by_integration:
        return list(
            latest_by_integration.values()
        )

    latest_legacy_scan = next(
        (
            scan
            for scan in scans
            if scan.integration_id
            is None
        ),
        None,
    )

    return (
        [latest_legacy_scan]
        if latest_legacy_scan
        is not None
        else []
    )


def get_integration_names(
    db: Session,
    integration_ids: set[int],
) -> dict[int, str]:
    if not integration_ids:
        return {}

    rows = db.execute(
        select(
            IntegrationRecord.id,
            IntegrationRecord.name,
        ).where(
            IntegrationRecord.id.in_(
                integration_ids
            )
        )
    ).all()

    return {
        int(row.id): str(row.name)
        for row in rows
    }


def get_visible_duplicate_snapshot(
    db: Session,
) -> tuple[
    list[dict[str, Any]],
    dict[int, dict[str, int]],
    dict[str, int],
]:
    """
    Build current duplicate metrics from the exact same visible
    Review Queue data used by the Duplicate Detection page.

    Reviewed/remediated pairs that are hidden from Duplicate Detection
    are therefore also excluded from the dashboard's current-state KPIs.
    Historical trend data remains based on the scan snapshot recorded at
    scan time.
    """

    cards = get_visible_review_summary(
        db=db,
    )

    applications: dict[
        str,
        dict[str, Any],
    ] = {}

    scan_totals: dict[
        int,
        dict[str, int],
    ] = {}

    totals = {
        "duplicateGroups": 0,
        "duplicateAccounts": 0,
        "highConfidenceMatches": 0,
    }

    for card in cards:
        if int(
            card.get(
                "duplicateGroups",
                0,
            )
            or 0
        ) <= 0:
            continue

        application = str(
            card.get(
                "application",
                "",
            )
            or ""
        ).strip()

        integration_id = (
            int(card["integrationId"])
            if card.get(
                "integrationId"
            )
            is not None
            else None
        )

        groups = (
            get_visible_duplicate_groups(
                db=db,
                application=application,
                integration_id=(
                    integration_id
                ),
            )
        )

        if not groups:
            continue

        duplicate_groups = len(
            groups
        )
        duplicate_accounts = sum(
            int(
                group.get(
                    "duplicates",
                    0,
                )
                or 0
            )
            for group in groups
        )
        high_confidence_groups = sum(
            1
            for group in groups
            if float(
                group.get(
                    "highestConfidence",
                    0,
                )
                or 0
            )
            >= 95
        )
        highest_confidence = max(
            float(
                group.get(
                    "highestConfidence",
                    0,
                )
                or 0
            )
            for group in groups
        )

        totals[
            "duplicateGroups"
        ] += duplicate_groups
        totals[
            "duplicateAccounts"
        ] += duplicate_accounts
        totals[
            "highConfidenceMatches"
        ] += high_confidence_groups

        scan_id = int(
            card["scanId"]
        )
        scan_summary = (
            scan_totals.setdefault(
                scan_id,
                {
                    "duplicateGroups": 0,
                    "duplicateAccounts": 0,
                    "highConfidenceMatches": 0,
                },
            )
        )
        scan_summary[
            "duplicateGroups"
        ] += duplicate_groups
        scan_summary[
            "duplicateAccounts"
        ] += duplicate_accounts
        scan_summary[
            "highConfidenceMatches"
        ] += high_confidence_groups

        key = normalize_application_name(
            application
        )
        current = applications.get(
            key
        )

        if current is None:
            applications[key] = {
                "application": application,
                "duplicateGroups": (
                    duplicate_groups
                ),
                "duplicateAccounts": (
                    duplicate_accounts
                ),
                "highestConfidence": (
                    highest_confidence
                ),
                "highConfidenceGroups": (
                    high_confidence_groups
                ),
            }
            continue

        current[
            "duplicateGroups"
        ] += duplicate_groups
        current[
            "duplicateAccounts"
        ] += duplicate_accounts
        current[
            "highConfidenceGroups"
        ] += high_confidence_groups
        current[
            "highestConfidence"
        ] = max(
            float(
                current[
                    "highestConfidence"
                ]
            ),
            highest_confidence,
        )

    application_statistics = list(
        applications.values()
    )
    application_statistics.sort(
        key=lambda item: (
            -int(
                item[
                    "duplicateAccounts"
                ]
            ),
            normalize_application_name(
                item[
                    "application"
                ]
            ),
        )
    )

    return (
        application_statistics,
        scan_totals,
        totals,
    )

def get_period_start(
    period: str,
) -> datetime:
    now = datetime.now()

    if period == "daily":
        return now - timedelta(
            days=1
        )

    if period == "weekly":
        return now - timedelta(
            days=7
        )

    if period == "monthly":
        return now - timedelta(
            days=30
        )

    if period == "yearly":
        return now - timedelta(
            days=365
        )

    raise ValueError(
        f"Unsupported dashboard period: {period}"
    )


def format_trend_label(
    created_at: datetime | None,
    scan_id: int,
    period: str,
) -> str:
    if created_at is None:
        return f"Scan {scan_id}"

    if period == "daily":
        return created_at.strftime(
            "%H:%M"
        )

    if period in {
        "weekly",
        "monthly",
    }:
        return created_at.strftime(
            "%d %b"
        )

    return created_at.strftime(
        "%b %Y"
    )


def get_scan_trend(
    db: Session,
    *,
    period: str,
) -> list[dict[str, Any]]:
    if period not in VALID_PERIODS:
        raise ValueError(
            f"Invalid dashboard period: {period}"
        )

    start_date = get_period_start(
        period
    )

    scans = list(
        db.scalars(
            select(ScanRecord)
            .where(
                ScanRecord.status
                == "COMPLETED",
                ScanRecord.created_at
                >= start_date,
            )
            .order_by(
                ScanRecord.created_at.asc(),
                ScanRecord.id.asc(),
            )
        ).all()
    )

    linked_scans_exist = any(
        scan.integration_id
        is not None
        for scan in scans
    )

    if linked_scans_exist:
        scans = [
            scan
            for scan in scans
            if scan.integration_id
            is not None
        ]

    if len(scans) > DASHBOARD_TREND_POINTS:
        scans = scans[-DASHBOARD_TREND_POINTS:]

    integration_ids = {
        int(scan.integration_id)
        for scan in scans
        if scan.integration_id
        is not None
    }

    integration_names = (
        get_integration_names(
            db,
            integration_ids,
        )
    )

    return [
        {
            "scanId": scan.id,
            "integrationId": (
                scan.integration_id
            ),
            "integrationName": (
                integration_names.get(
                    int(
                        scan.integration_id
                    )
                )
                if scan.integration_id
                is not None
                else None
            ),
            "name": format_trend_label(
                created_at=scan.created_at,
                scan_id=scan.id,
                period=period,
            ),
            "filename": scan.filename,
            "accountsScanned": (
                scan.accounts_scanned
            ),
            "duplicateGroups": (
                scan.duplicate_group_count
            ),
            "duplicateAccounts": (
                scan.duplicate_account_count
            ),
            "highConfidence": (
                scan.high_confidence_count
            ),
            "createdAt": (
                scan.created_at.isoformat()
                if scan.created_at
                else None
            ),
        }
        for scan in scans
    ]


def build_empty_dashboard_response(
    period: str,
) -> dict[str, Any]:
    return {
        "hasData": False,
        "period": period,
        "scan": None,
        "scans": [],
        "summary": {
            "accountsScanned": 0,
            "applications": 0,
            "integrations": 0,
            "duplicateGroups": 0,
            "duplicateAccounts": 0,
            "highConfidenceMatches": 0,
        },
        "applications": [],
        "applicationCount": 0,
        "trend": [],
    }


def build_dashboard_response(
    db: Session,
    period: str = "daily",
) -> dict[str, Any]:
    if period not in VALID_PERIODS:
        raise ValueError(
            f"Invalid dashboard period: {period}"
        )

    latest_scans = (
        get_latest_completed_scans_by_integration(
            db
        )
    )

    if not latest_scans:
        return (
            build_empty_dashboard_response(
                period
            )
        )

    latest_overall_scan = max(
        latest_scans,
        key=lambda scan: (
            scan.created_at,
            scan.id,
        ),
    )

    integration_ids = {
        int(scan.integration_id)
        for scan in latest_scans
        if scan.integration_id
        is not None
    }

    integration_names = (
        get_integration_names(
            db,
            integration_ids,
        )
    )

    (
        application_statistics,
        visible_scan_totals,
        visible_duplicate_totals,
    ) = get_visible_duplicate_snapshot(
        db
    )

    trend = get_scan_trend(
        db,
        period=period,
    )

    all_scan_summaries = [
        {
            "id": scan.id,
            "integrationId": (
                scan.integration_id
            ),
            "integrationName": (
                integration_names.get(
                    int(
                        scan.integration_id
                    )
                )
                if scan.integration_id
                is not None
                else None
            ),
            "filename": scan.filename,
            "status": scan.status,
            "createdAt": (
                scan.created_at.isoformat()
                if scan.created_at
                else None
            ),
            "accountsScanned": (
                scan.accounts_scanned
            ),
            "applications": (
                scan.application_count
            ),
            "duplicateGroups": (
                visible_scan_totals
                .get(
                    scan.id,
                    {},
                )
                .get(
                    "duplicateGroups",
                    0,
                )
            ),
            "duplicateAccounts": (
                visible_scan_totals
                .get(
                    scan.id,
                    {},
                )
                .get(
                    "duplicateAccounts",
                    0,
                )
            ),
            "highConfidenceMatches": (
                visible_scan_totals
                .get(
                    scan.id,
                    {},
                )
                .get(
                    "highConfidenceMatches",
                    0,
                )
            ),
        }
        for scan in sorted(
            latest_scans,
            key=lambda item: (
                item.created_at,
                item.id,
            ),
            reverse=True,
        )
    ]

    return {
        "hasData": True,
        "period": period,
        "scan": {
            "id": latest_overall_scan.id,
            "integrationId": (
                latest_overall_scan
                .integration_id
            ),
            "integrationName": (
                integration_names.get(
                    int(
                        latest_overall_scan
                        .integration_id
                    )
                )
                if latest_overall_scan
                .integration_id
                is not None
                else None
            ),
            "filename": (
                latest_overall_scan.filename
            ),
            "status": (
                latest_overall_scan.status
            ),
            "createdAt": (
                latest_overall_scan
                .created_at
                .isoformat()
                if latest_overall_scan
                .created_at
                else None
            ),
        },
        "scans": all_scan_summaries[:DASHBOARD_RECENT_SCANS],
        "summary": {
            "accountsScanned": sum(
                int(
                    scan.accounts_scanned
                    or 0
                )
                for scan in latest_scans
            ),
            "applications": sum(
                int(
                    scan.application_count
                    or 0
                )
                for scan in latest_scans
            ),
            "integrations": len(
                integration_ids
            ),
            "duplicateGroups": (
                visible_duplicate_totals[
                    "duplicateGroups"
                ]
            ),
            "duplicateAccounts": (
                visible_duplicate_totals[
                    "duplicateAccounts"
                ]
            ),
            "highConfidenceMatches": (
                visible_duplicate_totals[
                    "highConfidenceMatches"
                ]
            ),
        },
        "applications": application_statistics[:DASHBOARD_TOP_APPLICATIONS],
        "applicationCount": len(application_statistics),
        "trend": trend,
    }
