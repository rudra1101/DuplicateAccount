from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import (
    case,
    func,
    select,
)
from sqlalchemy.orm import Session

from app.db_models.duplicate_group import (
    DuplicateGroupRecord,
)
from app.db_models.integration import (
    IntegrationRecord,
)
from app.db_models.scan import (
    ScanRecord,
)


VALID_PERIODS = {
    "daily",
    "weekly",
    "monthly",
    "yearly",
}


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


def get_application_statistics(
    db: Session,
    *,
    scan_ids: list[int],
) -> list[dict[str, Any]]:
    if not scan_ids:
        return []

    statement = (
        select(
            DuplicateGroupRecord.application,
            func.count(
                DuplicateGroupRecord.id
            ).label(
                "duplicate_group_count"
            ),
            func.coalesce(
                func.sum(
                    DuplicateGroupRecord
                    .duplicate_count
                ),
                0,
            ).label(
                "duplicate_account_count"
            ),
            func.coalesce(
                func.max(
                    DuplicateGroupRecord
                    .highest_confidence
                ),
                0,
            ).label(
                "highest_confidence"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            DuplicateGroupRecord
                            .highest_confidence
                            >= 95,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label(
                "high_confidence_count"
            ),
        )
        .where(
            DuplicateGroupRecord.scan_id.in_(
                scan_ids
            )
        )
        .group_by(
            DuplicateGroupRecord.application
        )
        .order_by(
            func.sum(
                DuplicateGroupRecord
                .duplicate_count
            ).desc(),
            DuplicateGroupRecord
            .application
            .asc(),
        )
    )

    rows = db.execute(
        statement
    ).all()

    combined: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in rows:
        key = normalize_application_name(
            row.application
        )

        current = {
            "application": str(
                row.application or ""
            ).strip(),
            "duplicateGroups": int(
                row.duplicate_group_count
                or 0
            ),
            "duplicateAccounts": int(
                row.duplicate_account_count
                or 0
            ),
            "highestConfidence": float(
                row.highest_confidence
                or 0
            ),
            "highConfidenceGroups": int(
                row.high_confidence_count
                or 0
            ),
        }

        existing = combined.get(
            key
        )

        if existing is None:
            combined[key] = current
            continue

        existing[
            "duplicateGroups"
        ] += current[
            "duplicateGroups"
        ]

        existing[
            "duplicateAccounts"
        ] += current[
            "duplicateAccounts"
        ]

        existing[
            "highConfidenceGroups"
        ] += current[
            "highConfidenceGroups"
        ]

        existing[
            "highestConfidence"
        ] = max(
            float(
                existing[
                    "highestConfidence"
                ]
            ),
            float(
                current[
                    "highestConfidence"
                ]
            ),
        )

    result = list(
        combined.values()
    )

    result.sort(
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

    return result


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

    scan_ids = [
        scan.id
        for scan in latest_scans
    ]

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

    application_statistics = (
        get_application_statistics(
            db,
            scan_ids=scan_ids,
        )
    )

    trend = get_scan_trend(
        db,
        period=period,
    )

    scan_summaries = [
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
                scan.duplicate_group_count
            ),
            "duplicateAccounts": (
                scan.duplicate_account_count
            ),
            "highConfidenceMatches": (
                scan.high_confidence_count
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
        "scans": scan_summaries,
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
            "duplicateGroups": sum(
                int(
                    scan.duplicate_group_count
                    or 0
                )
                for scan in latest_scans
            ),
            "duplicateAccounts": sum(
                int(
                    scan.duplicate_account_count
                    or 0
                )
                for scan in latest_scans
            ),
            "highConfidenceMatches": sum(
                int(
                    scan.high_confidence_count
                    or 0
                )
                for scan in latest_scans
            ),
        },
        "applications": (
            application_statistics
        ),
        "trend": trend,
    }