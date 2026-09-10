from __future__ import annotations

import hashlib
import io
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.factory import ConnectorFactory
from app.db_models.account import AccountRecord
from app.db_models.application import ApplicationRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.services.account_loader import load_uploaded_accounts
from app.services.identity_ingestion_service import (
    authoritative_identity_count,
    replace_authoritative_identities,
)
from app.services.orphan_detection_service import detect_orphan_findings
from app.services.review_candidate_repository import save_review_candidates
from app.services.review_pair_feedback_service import load_pair_feedback
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


def _default_application_for_integration(db: Session, integration_id: int) -> str | None:
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


def _preserve_raw_attributes(db: Session, *, scan_id: int, accounts: list[Any]) -> None:
    stored_accounts = list(
        db.scalars(
            select(AccountRecord)
            .where(AccountRecord.scan_id == scan_id)
            .order_by(AccountRecord.id.asc())
        ).all()
    )
    for stored, source in zip(stored_accounts, accounts):
        payload = source.model_dump() if hasattr(source, "model_dump") else dict(source)
        raw = payload.get("rawAttributes") or payload.get("raw_attributes") or {}
        stored.raw_attributes = dict(raw) if isinstance(raw, dict) else {}
    db.commit()


def _complete_execution(
    db: Session,
    *,
    execution: JobExecutionRecord,
    source_file_name: str,
    source_path: str | None,
    checksum: str,
    processed_count: int,
    scan_id: int | None = None,
    duplicate_groups: int = 0,
    duplicate_accounts: int = 0,
) -> JobExecutionRecord:
    execution.scan_id = scan_id
    execution.status = "COMPLETED"
    execution.source_file_name = source_file_name
    execution.source_path = source_path
    execution.file_checksum = checksum
    execution.accounts_scanned = processed_count
    execution.duplicate_groups = duplicate_groups
    execution.duplicate_accounts = duplicate_accounts
    execution.completed_at = datetime.utcnow()
    execution.error_message = None
    db.commit()
    db.refresh(execution)
    return execution


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
        records = load_uploaded_accounts(
            io.BytesIO(connector_file.content),
            delimiter=delimiter,
            encoding=encoding,
            default_application=_default_application_for_integration(db, integration.id),
            allow_dynamic_schema=True,
        )

        if integration.source_purpose == "AUTHORITATIVE":
            identity_count = replace_authoritative_identities(
                db,
                integration_id=integration.id,
                identities=records,
            )
            print(
                "[Authoritative Identity Ingestion] "
                f"Integration={integration.id}, IdentitiesLoaded={identity_count}"
            )
            return _complete_execution(
                db,
                execution=execution,
                source_file_name=connector_file.filename,
                source_path=connector_file.source_path,
                checksum=checksum,
                processed_count=identity_count,
            )

        pair_feedback = load_pair_feedback(db, integration_id=integration.id)
        print(
            "[Reviewer Feedback] "
            f"Integration={integration.id}, DurablePairsLoaded={len(pair_feedback)}"
        )

        duplicate_groups, duplicate_details, review_candidates = analyze_duplicate_decisions(
            records,
            pair_feedback=pair_feedback,
        )

        scan = save_completed_scan(
            db=db,
            integration_id=integration.id,
            filename=connector_file.filename,
            accounts=records,
            duplicate_groups=duplicate_groups,
            duplicate_details=duplicate_details,
        )
        _preserve_raw_attributes(db, scan_id=scan.id, accounts=records)

        saved_review_candidates = save_review_candidates(
            db,
            scan_id=scan.id,
            candidates=review_candidates,
        )
        print(
            "[Duplicate Detection] "
            f"ApplicationReviewCandidatesPersisted={saved_review_candidates}"
        )

        identity_count = authoritative_identity_count(db)
        if identity_count > 0:
            orphan_findings = detect_orphan_findings(db, scan_id=scan.id)
            print(
                "[Orphan Detection] "
                f"AuthoritativeIdentities={identity_count}, OrphanFindings={len(orphan_findings)}"
            )
        else:
            print("[Orphan Detection] Skipped: no authoritative identities loaded.")

        total_duplicate_groups = sum(len(groups) for groups in duplicate_groups.values())
        total_duplicate_accounts = sum(
            int(group.get("duplicates", 0) or 0)
            for groups in duplicate_groups.values()
            for group in groups
        )

        return _complete_execution(
            db,
            execution=execution,
            source_file_name=connector_file.filename,
            source_path=connector_file.source_path,
            checksum=checksum,
            processed_count=len(records),
            scan_id=scan.id,
            duplicate_groups=total_duplicate_groups,
            duplicate_accounts=total_duplicate_accounts,
        )

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
