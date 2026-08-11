from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.ai.vector_store import (
    account_vector_index_service,
)
from app.db_models import (
    AccountRecord,
    DuplicateCandidateRecord,
    DuplicateGroupRecord,
    ScanRecord,
)


logger = logging.getLogger(__name__)


def account_to_dict(
    account: Any,
) -> dict[str, Any]:
    if isinstance(account, Mapping):
        return dict(account)

    if hasattr(account, "model_dump"):
        return account.model_dump()

    raise TypeError(
        "Unsupported account type: "
        f"{type(account).__name__}"
    )


def normalize_optional_value(
    value: Any,
) -> Any:
    if value is None:
        return None

    if isinstance(value, str):
        normalized = value.strip()

        if not normalized:
            return None

        return normalized

    return value


def save_completed_scan(
    db: Session,
    *,
    integration_id: int | None,
    filename: str,
    accounts: list[Any],
    duplicate_groups: dict[
        str,
        list[dict[str, Any]],
    ],
    duplicate_details: dict[
        int,
        dict[str, Any],
    ],
) -> ScanRecord:
    """
    Persist a completed scan and its duplicate results.

    Every scan is linked to the integration that produced it.
    This allows the review queue to resolve the latest completed
    scan separately for each integration.

    Database records are committed first. Account vectors are
    indexed afterward. A FAISS failure does not roll back the
    completed database scan.
    """

    account_payloads = [
        account_to_dict(account)
        for account in accounts
    ]

    duplicate_group_count = sum(
        len(groups)
        for groups
        in duplicate_groups.values()
    )

    duplicate_account_count = sum(
        int(
            group.get(
                "duplicates",
                0,
            )
            or 0
        )
        for groups
        in duplicate_groups.values()
        for group
        in groups
    )

    high_confidence_count = sum(
        1
        for groups
        in duplicate_groups.values()
        for group
        in groups
        if float(
            group.get(
                "highestConfidence",
                0,
            )
            or 0
        )
        >= 95
    )

    application_names = {
        str(
            account_data.get(
                "application",
                "",
            )
            or ""
        ).strip()
        for account_data
        in account_payloads
        if str(
            account_data.get(
                "application",
                "",
            )
            or ""
        ).strip()
    }

    scan = ScanRecord(
        integration_id=integration_id,
        filename=filename,
        status="COMPLETED",
        accounts_scanned=len(
            account_payloads
        ),
        application_count=len(
            application_names
        ),
        duplicate_group_count=(
            duplicate_group_count
        ),
        duplicate_account_count=(
            duplicate_account_count
        ),
        high_confidence_count=(
            high_confidence_count
        ),
    )

    db.add(scan)
    db.flush()

    account_record_ids: list[int] = []

    try:
        for account_data in account_payloads:
            account_record = AccountRecord(
                scan_id=scan.id,
                source_account_id=str(
                    account_data.get(
                        "id",
                        "",
                    )
                    or ""
                ),
                application=str(
                    account_data.get(
                        "application",
                        "",
                    )
                    or ""
                ),
                username=str(
                    account_data.get(
                        "username",
                        "",
                    )
                    or ""
                ),
                display_name=str(
                    account_data.get(
                        "displayName",
                        "",
                    )
                    or ""
                ),
                email=str(
                    account_data.get(
                        "email",
                        "",
                    )
                    or ""
                ),
                employee_id=(
                    normalize_optional_value(
                        account_data.get(
                            "employeeId"
                        )
                    )
                ),
                department=(
                    normalize_optional_value(
                        account_data.get(
                            "department"
                        )
                    )
                ),
                manager=(
                    normalize_optional_value(
                        account_data.get(
                            "manager"
                        )
                    )
                ),
                status=(
                    normalize_optional_value(
                        account_data.get(
                            "status"
                        )
                    )
                ),
                created=(
                    normalize_optional_value(
                        account_data.get(
                            "created"
                        )
                    )
                ),
            )

            db.add(account_record)
            db.flush()

            account_record_ids.append(
                account_record.id
            )

        for (
            application,
            groups,
        ) in duplicate_groups.items():
            for group in groups:
                original_group_id = int(
                    group["groupId"]
                )

                group_record = (
                    DuplicateGroupRecord(
                        scan_id=scan.id,
                        application=(
                            application
                        ),
                        primary_username=str(
                            group.get(
                                "primaryAccount",
                                "",
                            )
                            or ""
                        ),
                        duplicate_count=int(
                            group.get(
                                "duplicates",
                                0,
                            )
                            or 0
                        ),
                        highest_confidence=float(
                            group.get(
                                "highestConfidence",
                                0,
                            )
                            or 0
                        ),
                    )
                )

                db.add(group_record)
                db.flush()

                detail = (
                    duplicate_details.get(
                        original_group_id,
                        {},
                    )
                )

                candidates = detail.get(
                    "duplicates",
                    [],
                )

                for candidate in candidates:
                    candidate_account = (
                        candidate.get(
                            "account",
                            {},
                        )
                        or {}
                    )

                    candidate_record = (
                        DuplicateCandidateRecord(
                            group_id=(
                                group_record.id
                            ),
                            candidate_number=int(
                                candidate.get(
                                    "id",
                                    0,
                                )
                                or 0
                            ),
                            username=str(
                                candidate_account.get(
                                    "username",
                                    "",
                                )
                                or ""
                            ),
                            confidence=float(
                                candidate.get(
                                    "confidence",
                                    0,
                                )
                                or 0
                            ),
                            recommendation=str(
                                candidate.get(
                                    "recommendation",
                                    "REVIEW",
                                )
                                or "REVIEW"
                            ),
                            matched_attributes=(
                                candidate.get(
                                    "matchedAttributes",
                                    [],
                                )
                                or []
                            ),
                            different_attributes=(
                                candidate.get(
                                    "differentAttributes",
                                    [],
                                )
                                or []
                            ),
                            account_data=(
                                candidate_account
                            ),
                            classification=(
                                candidate.get(
                                    "classification"
                                )
                            ),
                            model_version=(
                                candidate.get(
                                    "modelVersion"
                                )
                            ),
                            reasons=(
                                candidate.get(
                                    "reasons",
                                    [],
                                )
                                or []
                            ),
                            warnings=(
                                candidate.get(
                                    "warnings",
                                    [],
                                )
                                or []
                            ),
                            features=(
                                candidate.get(
                                    "features",
                                    {},
                                )
                                or {}
                            ),
                        )
                    )

                    db.add(
                        candidate_record
                    )

        db.commit()
        db.refresh(scan)

    except Exception:
        db.rollback()

        logger.exception(
            "Failed to persist completed scan "
            "for integration %s and file '%s'.",
            integration_id,
            filename,
        )

        raise

    try:
        indexed_count = (
            account_vector_index_service
            .index_accounts(
                scan_id=scan.id,
                accounts=account_payloads,
                account_record_ids=(
                    account_record_ids
                ),
            )
        )

        logger.info(
            "Indexed %s account vector(s) "
            "for scan %s and integration %s.",
            indexed_count,
            scan.id,
            integration_id,
        )

    except ValueError as exc:
        message = str(exc)

        if (
            "Vector IDs already exist"
            in message
        ):
            logger.warning(
                "FAISS vectors for scan %s "
                "already exist. Skipping "
                "duplicate indexing.",
                scan.id,
            )

        else:
            logger.exception(
                "FAISS indexing failed for "
                "scan %s. Database scan data "
                "was saved successfully.",
                scan.id,
            )

    except Exception:
        logger.exception(
            "FAISS indexing failed for scan %s. "
            "Database scan data was saved "
            "successfully.",
            scan.id,
        )

    return scan