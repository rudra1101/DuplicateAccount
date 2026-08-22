from __future__ import annotations

import hashlib
import io
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.factory import ConnectorFactory
from app.db_models.application import ApplicationRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.services.account_loader import load_uploaded_accounts
from app.services.review_candidate_repository import save_review_candidates
from app.services.scan_repository import save_completed_scan
from app.services.single_pass_duplicate_service import analyze_duplicate_decisions


UTC_ZONE = ZoneInfo("UTC")
INDIA_ZONE = ZoneInfo("Asia/Kolkata")


def calculate_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _to_india_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC_ZONE)
    return value.astimezone(INDIA_ZONE).isoformat()


def execution_to_dict(execution: JobExecutionRecord) -> dict[str, Any]:
    return {
        "executionId": execution.id,
        "integrationId": execution.integration_id,
        "scanId": execution.scan_id,
        "status": execution.status,
        "sourceFileName": execution.source_file_name,
        "sourcePath": execution.source_path,
        "fileChecksum": execution.file_checksum,
        "accountsScanned": execution.accounts_scanned,
        "duplicateGroups": execution.duplicate_groups,
        "duplicateAccounts": execution.duplicate_accounts,
        "errorMessage": execution.error_message,
        "startedAt": _to_india_iso(execution.started_at),
        "completedAt": _to_india_iso(execution.completed_at),
    }


def _default_application_for_integration(
    db: Session,
    integration_id: int,
) -> str | None:
    applications = list(
        db.scalars(
            select(ApplicationRecord)
            .where(
                ApplicationRecord.integration_id == integration_id,
                ApplicationRecord.enabled.is_(True),
            )
            .order_by(ApplicationRecord.id.asc())
        ).all()
    )

    if len(applications) == 1:
        return applications[0].name

    return None


def execute_integration(
    db: Session,
    *,
    integration: IntegrationRecord,
    secrets: dict[str, str] | None = None,
) -> JobExecutionRecord:
    if not integration.enabled:
        raise ValueError("The integration is disabled.")

    execution = JobExecutionRecord(
        integration_id=integration.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
        accounts_scanned=0,
        duplicate_groups=0,
        duplicate_accounts=0,
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    try:
        connector = ConnectorFactory.create(
            connector_type=integration.connector_type,
            configuration=integration.configuration,
            secrets=secrets,
        )

        with connector:
            connector_file = connector.fetch_file()

        checksum = calculate_checksum(connector_file.content)
        configuration = integration.configuration or {}
        delimiter = str(configuration.get("delimiter", ","))
        encoding = str(configuration.get("encoding", "utf-8-sig"))

        accounts = load_uploaded_accounts(
            io.BytesIO(connector_file.content),
            delimiter=delimiter,
            encoding=encoding,
            default_application=_default_application_for_integration(db, integration.id),
            allow_dynamic_schema=True,
        )

        (
            duplicate_groups,
            duplicate_details,
            review_candidates,
        ) = analyze_duplicate_decisions(accounts)

        scan = save_completed_scan(
            db=db,
            integration_id=integration.id,
            filename=connector_file.filename,
            accounts=accounts,
            duplicate_groups=duplicate_groups,
            duplicate_details=duplicate_details,
        )

        saved_review_candidates = save_review_candidates(
            db,
            scan_id=scan.id,
            candidates=review_candidates,
        )
        print(
            "[Duplicate Detection] "
            f"ApplicationReviewCandidatesPersisted={saved_review_candidates}"
        )

        total_duplicate_groups = sum(len(groups) for groups in duplicate_groups.values())
        total_duplicate_accounts = sum(
            int(group.get("duplicates", 0) or 0)
            for groups in duplicate_groups.values()
            for group in groups
        )

        execution.scan_id = scan.id
        execution.status = "COMPLETED"
        execution.source_file_name = connector_file.filename
        execution.source_path = connector_file.source_path
        execution.file_checksum = checksum
        execution.accounts_scanned = len(accounts)
        execution.duplicate_groups = total_duplicate_groups
        execution.duplicate_accounts = total_duplicate_accounts
        execution.completed_at = datetime.utcnow()
        execution.error_message = None

        db.commit()
        db.refresh(execution)
        return execution

    except Exception as exc:
        db.rollback()

        failed_execution = db.get(JobExecutionRecord, execution.id)
        if failed_execution is not None:
            failed_execution.status = "FAILED"
            failed_execution.error_message = str(exc)
            failed_execution.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(failed_execution)

        raise
