from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    case,
    func,
    select,
)
from sqlalchemy.orm import Session

from app.db_models.account import (
    AccountRecord,
)
from app.db_models.duplicate_candidate import (
    DuplicateCandidateRecord,
)
from app.db_models.duplicate_group import (
    DuplicateGroupRecord,
)
from app.db_models.integration import (
    IntegrationRecord,
)
from app.db_models.scan import (
    ScanRecord,
)
from app.services.training_label_service import (
    create_training_label,
    get_training_label_summary,
    normalize_training_label,
)


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
    integration_id: int | None = None,
) -> list[ScanRecord]:
    """
    Return the latest completed scan for each integration.

    When integration_id is provided, return only the latest
    completed scan for that integration.
    """

    statement = (
        select(ScanRecord)
        .where(
            ScanRecord.status
            == "COMPLETED"
        )
    )

    if integration_id is not None:
        statement = statement.where(
            ScanRecord.integration_id
            == integration_id
        )

    statement = statement.order_by(
        ScanRecord.created_at.desc(),
        ScanRecord.id.desc(),
    )

    scans = list(
        db.scalars(
            statement
        ).all()
    )

    if integration_id is not None:
        return (
            [scans[0]]
            if scans
            else []
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
        current_integration_id = int(
            scan.integration_id
        )

        if (
            current_integration_id
            not in latest_by_integration
        ):
            latest_by_integration[
                current_integration_id
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

def get_latest_completed_scan(
    db: Session,
) -> ScanRecord | None:
    scans = (
        get_latest_completed_scans_by_integration(
            db
        )
    )

    if not scans:
        return None

    return max(
        scans,
        key=lambda scan: (
            scan.created_at,
            scan.id,
        ),
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
        )
        .where(
            IntegrationRecord.id.in_(
                integration_ids
            )
        )
    ).all()

    return {
        int(row.id): str(row.name)
        for row in rows
    }


def get_review_summary(
    db: Session,
    integration_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Return one Review Queue card per application.

    The latest completed scan is selected for each integration.
    When integration_id is supplied, only that integration is used.

    Applications are loaded from AccountRecord so applications with
    zero duplicate groups still appear in the Review Queue.
    """

    latest_scans = (
        get_latest_completed_scans_by_integration(
            db=db,
            integration_id=integration_id,
        )
    )

    if not latest_scans:
        return []

    integration_ids = {
        int(scan.integration_id)
        for scan in latest_scans
        if scan.integration_id
        is not None
    }

    integration_names = (
        get_integration_names(
            db=db,
            integration_ids=(
                integration_ids
            ),
        )
    )

    cards: list[
        dict[str, Any]
    ] = []

    for scan in latest_scans:
        account_rows = db.execute(
            select(
                AccountRecord.application,
                func.count(
                    AccountRecord.id
                ).label(
                    "total_accounts"
                ),
            )
            .where(
                AccountRecord.scan_id
                == scan.id
            )
            .group_by(
                AccountRecord.application
            )
            .order_by(
                AccountRecord.application.asc()
            )
        ).all()

        duplicate_rows = db.execute(
            select(
                DuplicateGroupRecord.application,
                func.count(
                    DuplicateGroupRecord.id
                ).label(
                    "duplicate_groups"
                ),
                func.coalesce(
                    func.sum(
                        DuplicateGroupRecord
                        .duplicate_count
                    ),
                    0,
                ).label(
                    "duplicate_accounts"
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
                    "high_confidence"
                ),
            )
            .where(
                DuplicateGroupRecord.scan_id
                == scan.id
            )
            .group_by(
                DuplicateGroupRecord.application
            )
        ).all()

        duplicate_by_application = {
            normalize_application_name(
                row.application
            ): row
            for row in duplicate_rows
        }

        current_integration_id = (
            int(scan.integration_id)
            if scan.integration_id
            is not None
            else None
        )

        for account_row in account_rows:
            application = str(
                account_row.application
                or "Unknown"
            ).strip()

            duplicate_row = (
                duplicate_by_application.get(
                    normalize_application_name(
                        application
                    )
                )
            )

            cards.append(
                {
                    "integrationId": (
                        current_integration_id
                    ),
                    "integrationName": (
                        integration_names.get(
                            current_integration_id
                        )
                        if current_integration_id
                        is not None
                        else None
                    ),
                    "scanId": scan.id,
                    "application": application,
                    "totalAccounts": int(
                        account_row.total_accounts
                        or 0
                    ),
                    "duplicateGroups": (
                        int(
                            duplicate_row
                            .duplicate_groups
                            or 0
                        )
                        if duplicate_row
                        is not None
                        else 0
                    ),
                    "duplicateAccounts": (
                        int(
                            duplicate_row
                            .duplicate_accounts
                            or 0
                        )
                        if duplicate_row
                        is not None
                        else 0
                    ),
                    "highConfidence": (
                        int(
                            duplicate_row
                            .high_confidence
                            or 0
                        )
                        if duplicate_row
                        is not None
                        else 0
                    ),
                    "lastScan": (
                        scan.created_at.isoformat()
                        if scan.created_at
                        else None
                    ),
                }
            )

    cards.sort(
        key=lambda card: (
            normalize_application_name(
                card["application"]
            ),
            card["integrationId"]
            or 0,
        )
    )

    return cards

def get_duplicate_groups(
    db: Session,
    application: str,
    integration_id: int | None = None,
) -> list[dict[str, Any]]:
    latest_scans = (
        get_latest_completed_scans_by_integration(
            db=db,
            integration_id=integration_id,
        )
    )

    if not latest_scans:
        return []

    scan_ids = [
        scan.id
        for scan in latest_scans
    ]

    normalized_application = (
        normalize_application_name(
            application
        )
    )

    groups = list(
        db.scalars(
            select(
                DuplicateGroupRecord
            )
            .where(
                DuplicateGroupRecord.scan_id.in_(
                    scan_ids
                )
            )
            .order_by(
                DuplicateGroupRecord
                .highest_confidence
                .desc(),
                DuplicateGroupRecord.id.asc(),
            )
        ).all()
    )

    matching_groups = [
        group
        for group in groups
        if normalize_application_name(
            group.application
        )
        == normalized_application
    ]

    return [
        {
            "groupId": group.id,
            "primaryAccount": (
                group.primary_username
            ),
            "duplicates": (
                group.duplicate_count
            ),
            "highestConfidence": (
                group.highest_confidence
            ),
            "scanId": group.scan_id,
        }
        for group in matching_groups
    ]


def get_account_snapshot(
    db: Session,
    *,
    scan_id: int,
    application: str,
    username: str,
) -> dict[str, Any] | None:
    account = db.scalars(
        select(
            AccountRecord
        )
        .where(
            AccountRecord.scan_id
            == scan_id,
            AccountRecord.application
            == application,
            AccountRecord.username
            == username,
        )
        .order_by(
            AccountRecord.id.asc()
        )
        .limit(1)
    ).first()

    if account is None:
        return None

    return {
        "id": (
            account.source_account_id
        ),
        "application": (
            account.application
        ),
        "username": (
            account.username
        ),
        "displayName": (
            account.display_name
        ),
        "email": account.email,
        "employeeId": (
            account.employee_id
        ),
        "department": (
            account.department
        ),
        "manager": (
            account.manager
        ),
        "status": account.status,
        "created": account.created,
    }


def get_duplicate_group_details(
    db: Session,
    group_id: int,
    integration_id: int | None = None,
) -> dict[str, Any] | None:
    group = db.get(
        DuplicateGroupRecord,
        group_id,
    )

    if group is None:
        return None

    latest_scan_ids = {
        scan.id
        for scan
        in get_latest_completed_scans_by_integration(
            db=db,
            integration_id=integration_id,
        )
    }

    if group.scan_id not in latest_scan_ids:
        return None

    primary_account = (
        get_account_snapshot(
            db=db,
            scan_id=group.scan_id,
            application=(
                group.application
            ),
            username=(
                group.primary_username
            ),
        )
    )

    if primary_account is None:
        primary_account = {
            "id": None,
            "application": (
                group.application
            ),
            "username": (
                group.primary_username
            ),
            "displayName": "",
            "email": "",
            "employeeId": None,
            "department": None,
            "manager": None,
            "status": None,
            "created": None,
        }

    candidates = list(
        db.scalars(
            select(
                DuplicateCandidateRecord
            )
            .where(
                DuplicateCandidateRecord.group_id
                == group.id
            )
            .order_by(
                DuplicateCandidateRecord
                .confidence
                .desc(),
                DuplicateCandidateRecord
                .candidate_number
                .asc(),
                DuplicateCandidateRecord
                .id
                .asc(),
            )
        ).all()
    )

    return {
        "groupId": group.id,
        "scanId": group.scan_id,
        "application": (
            group.application
        ),
        "highestConfidence": (
            group.highest_confidence
        ),
        "primaryAccount": (
            primary_account
        ),
        "duplicates": [
            {
                "id": (
                    candidate
                    .candidate_number
                ),
                "candidateRecordId": (
                    candidate.id
                ),
                "confidence": (
                    candidate.confidence
                ),
                "recommendation": (
                    candidate
                    .recommendation
                ),
                "classification": (
                    candidate
                    .classification
                ),
                "modelVersion": (
                    candidate
                    .model_version
                ),
                "matchedAttributes": (
                    candidate
                    .matched_attributes
                    or []
                ),
                "differentAttributes": (
                    candidate
                    .different_attributes
                    or []
                ),
                "reasons": (
                    candidate.reasons
                    or []
                ),
                "warnings": (
                    candidate.warnings
                    or []
                ),
                "features": (
                    candidate.features
                    or {}
                ),
                "account": (
                    candidate.account_data
                    or {}
                ),
                "reviewDecision": (
                    candidate.review_decision
                ),
                "reviewComment": (
                    candidate.review_comment
                ),
                "reviewerName": (
                    candidate.reviewer_name
                ),
                "reviewedAt": (
                    candidate.reviewed_at.isoformat()
                    if candidate.reviewed_at
                    else None
                ),
            }
            for candidate in candidates
        ],
    }


def get_scan_status(
    db: Session,
    integration_id: int | None = None,
) -> dict[str, Any]:
    latest_scans = (
        get_latest_completed_scans_by_integration(
            db=db,
            integration_id=integration_id,
        )
    )

    if not latest_scans:
        return {
            "accounts": 0,
            "applications": 0,
            "integrations": 0,
            "lastScan": None,
        }

    latest_scan = max(
        latest_scans,
        key=lambda scan: (
            scan.created_at,
            scan.id,
        ),
    )

    return {
        "accounts": sum(
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
            {
                scan.integration_id
                for scan in latest_scans
                if scan.integration_id
                is not None
            }
        ),
        "lastScan": (
            latest_scan
            .created_at
            .isoformat()
            if latest_scan.created_at
            else None
        ),
    }


def save_candidate_decision(
    db: Session,
    *,
    candidate_id: int,
    decision: str,
    comment: str | None = None,
    reviewer_name: str | None = None,
) -> dict[str, Any]:
    normalized_decision = (
        normalize_training_label(
            decision
        )
    )

    candidate = db.get(
        DuplicateCandidateRecord,
        candidate_id,
    )

    if candidate is None:
        raise ValueError(
            "Duplicate candidate was not found."
        )

    reviewed_at = datetime.now()

    candidate.review_decision = (
        normalized_decision
    )

    candidate.review_comment = (
        comment.strip()
        if comment
        and comment.strip()
        else None
    )

    candidate.reviewer_name = (
        reviewer_name.strip()
        if reviewer_name
        and reviewer_name.strip()
        else None
    )

    candidate.reviewed_at = (
        reviewed_at
    )

    try:
        training_label = (
            create_training_label(
                db=db,
                candidate_id=(
                    candidate.id
                ),
                label=(
                    normalized_decision
                ),
                reviewer_comment=(
                    candidate
                    .review_comment
                ),
                reviewer_name=(
                    candidate
                    .reviewer_name
                ),
                commit=False,
            )
        )

        db.commit()
        db.refresh(
            candidate
        )
        db.refresh(
            training_label
        )

    except Exception:
        db.rollback()
        raise

    summary = (
        get_training_label_summary(
            db
        )
    )

    return {
        "candidateId": (
            candidate.id
        ),
        "decision": (
            candidate.review_decision
        ),
        "comment": (
            candidate.review_comment
        ),
        "reviewerName": (
            candidate.reviewer_name
        ),
        "reviewedAt": (
            candidate
            .reviewed_at
            .isoformat()
            if candidate.reviewed_at
            else None
        ),
        "trainingLabelId": (
            training_label.id
        ),
        "labelSummary": summary,
    }