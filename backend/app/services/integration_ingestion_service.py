from __future__ import annotations

import hashlib
import io
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.connectors.factory import ConnectorFactory
from app.db_models.account import AccountRecord
from app.db_models.application import ApplicationRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.services.account_loader import load_uploaded_accounts
from app.services.correlation_policy_service import get_policy_for_account_integration
from app.services.identity_ingestion_service import authoritative_identity_count, replace_authoritative_identities
from app.services.orphan_detection_service import detect_orphan_findings
from app.services.review_candidate_repository import save_review_candidates
from app.services.review_pair_feedback_service import load_pair_feedback
from app.services.scan_repository import save_completed_scan
from app.services.schema_duplicate_service import detect_schema_duplicate_results
from app.services.single_pass_duplicate_service import analyze_duplicate_decisions
from app.services.source_account_inventory_service import (
    normalize_aggregation_type,
    persist_duplicate_findings,
    upsert_source_accounts,
)

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
        "aggregationType": execution.aggregation_type,
        "sourceFileName": execution.source_file_name,
        "sourcePath": execution.source_path,
        "fileChecksum": execution.file_checksum,
        "accountsScanned": execution.accounts_scanned,
        "accountsCreated": execution.accounts_created,
        "accountsUpdated": execution.accounts_updated,
        "accountsUnchanged": execution.accounts_unchanged,
        "accountsDeleted": execution.accounts_deleted,
        "duplicateGroups": execution.duplicate_groups,
        "duplicateAccounts": execution.duplicate_accounts,
        "errorMessage": execution.error_message,
        "startedAt": _to_india_iso(execution.started_at),
        "completedAt": _to_india_iso(execution.completed_at),
    }


def _applications_for_integration(db: Session, integration_id: int) -> list[ApplicationRecord]:
    return list(
        db.scalars(
            select(ApplicationRecord)
            .options(selectinload(ApplicationRecord.schemas))
            .where(ApplicationRecord.integration_id == integration_id, ApplicationRecord.enabled.is_(True))
            .order_by(ApplicationRecord.id.asc())
        ).all()
    )


def _default_application_for_integration(db: Session, integration_id: int) -> str | None:
    applications = _applications_for_integration(db, integration_id)
    return applications[0].name if len(applications) == 1 else None


def _native_identity_attributes_for_integration(db: Session, integration_id: int) -> dict[str, str]:
    result: dict[str, str] = {}
    for application in _applications_for_integration(db, integration_id):
        schema = next((item for item in application.schemas if item.is_active), None)
        if schema and schema.native_identity_attribute:
            result[application.name] = schema.native_identity_attribute
    return result


def _preserve_raw_attributes(db: Session, *, scan_id: int, accounts: list[Any]) -> None:
    stored_accounts = list(db.scalars(select(AccountRecord).where(AccountRecord.scan_id == scan_id).order_by(AccountRecord.id.asc())).all())
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
    inventory_stats: dict[str, int] | None = None,
    scan_id: int | None = None,
    duplicate_groups: int = 0,
    duplicate_accounts: int = 0,
) -> JobExecutionRecord:
    stats = inventory_stats or {}
    execution.scan_id = scan_id
    execution.status = "COMPLETED"
    execution.source_file_name = source_file_name
    execution.source_path = source_path
    execution.file_checksum = checksum
    execution.accounts_scanned = processed_count
    execution.accounts_created = int(stats.get("created", 0))
    execution.accounts_updated = int(stats.get("updated", 0))
    execution.accounts_unchanged = int(stats.get("unchanged", 0))
    execution.accounts_deleted = int(stats.get("deleted", 0))
    execution.duplicate_groups = duplicate_groups
    execution.duplicate_accounts = duplicate_accounts
    execution.completed_at = datetime.utcnow()
    execution.error_message = None
    db.commit()
    db.refresh(execution)
    return execution


def _merge_schema_results(duplicate_groups, duplicate_details, schema_groups, schema_details) -> None:
    represented: set[tuple[str, str]] = set()
    for detail in duplicate_details.values():
        primary = detail.get("primaryAccount") or {}
        app = str(primary.get("application") or "").strip().lower()
        native = str(primary.get("id") or "").strip().lower()
        if app and native:
            represented.add((app, native))
        for candidate in detail.get("duplicates") or []:
            account = candidate.get("account") or {}
            app = str(account.get("application") or "").strip().lower()
            native = str(account.get("id") or "").strip().lower()
            if app and native:
                represented.add((app, native))

    for application, groups in schema_groups.items():
        for group in groups:
            detail = schema_details.get(int(group["groupId"]), {})
            accounts = [detail.get("primaryAccount") or {}] + [item.get("account") or {} for item in detail.get("duplicates") or []]
            keys = {
                (str(account.get("application") or application).strip().lower(), str(account.get("id") or "").strip().lower())
                for account in accounts if str(account.get("id") or "").strip()
            }
            if keys and keys.intersection(represented):
                continue
            duplicate_groups.setdefault(application, []).append(group)
            duplicate_details[int(group["groupId"])] = detail
            represented.update(keys)


def execute_integration(
    db: Session,
    *,
    integration: IntegrationRecord,
    aggregation_type: str = "FULL",
    secrets: dict[str, str] | None = None,
) -> JobExecutionRecord:
    if not integration.enabled:
        raise ValueError("The integration is disabled.")

    mode = normalize_aggregation_type(aggregation_type)
    execution = JobExecutionRecord(
        integration_id=integration.id,
        status="RUNNING",
        aggregation_type=mode,
        started_at=datetime.utcnow(),
        accounts_scanned=0,
        accounts_created=0,
        accounts_updated=0,
        accounts_unchanged=0,
        accounts_deleted=0,
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
        records = load_uploaded_accounts(
            io.BytesIO(connector_file.content),
            delimiter=str(configuration.get("delimiter", ",")),
            encoding=str(configuration.get("encoding", "utf-8-sig")),
            default_application=_default_application_for_integration(db, integration.id),
            allow_dynamic_schema=True,
            native_identity_attributes=_native_identity_attributes_for_integration(db, integration.id),
        )

        if integration.source_purpose == "AUTHORITATIVE":
            if mode == "DELTA":
                raise ValueError("DELTA aggregation for authoritative sources is not enabled yet. Run a FULL aggregation until authoritative identity upsert is implemented.")
            inventory_stats = upsert_source_accounts(
                db, integration_id=integration.id, accounts=records, scan_id=None, aggregation_type=mode
            )
            identity_count = replace_authoritative_identities(db, integration_id=integration.id, identities=records)
            return _complete_execution(
                db, execution=execution, source_file_name=connector_file.filename,
                source_path=connector_file.source_path, checksum=checksum,
                processed_count=identity_count, inventory_stats=inventory_stats,
            )

        if mode == "DELTA":
            scan = save_completed_scan(
                db=db, integration_id=integration.id, filename=connector_file.filename,
                accounts=records, duplicate_groups={}, duplicate_details={},
            )
            _preserve_raw_attributes(db, scan_id=scan.id, accounts=records)
            inventory_stats = upsert_source_accounts(
                db, integration_id=integration.id, accounts=records, scan_id=scan.id, aggregation_type=mode
            )
            print(f"[Delta Aggregation] Integration={integration.id}, Stats={inventory_stats}. Duplicate/orphan re-evaluation deferred.")
            return _complete_execution(
                db, execution=execution, source_file_name=connector_file.filename,
                source_path=connector_file.source_path, checksum=checksum,
                processed_count=len(records), inventory_stats=inventory_stats, scan_id=scan.id,
            )

        pair_feedback = load_pair_feedback(db, integration_id=integration.id)
        duplicate_groups, duplicate_details, review_candidates = analyze_duplicate_decisions(records, pair_feedback=pair_feedback)
        next_group_id = max(duplicate_details.keys(), default=0) + 1
        schema_groups, schema_details = detect_schema_duplicate_results(
            db, integration_id=integration.id, accounts=records, starting_group_id=next_group_id
        )
        _merge_schema_results(duplicate_groups, duplicate_details, schema_groups, schema_details)

        scan = save_completed_scan(
            db=db, integration_id=integration.id, filename=connector_file.filename,
            accounts=records, duplicate_groups=duplicate_groups, duplicate_details=duplicate_details,
        )
        _preserve_raw_attributes(db, scan_id=scan.id, accounts=records)
        inventory_stats = upsert_source_accounts(
            db, integration_id=integration.id, accounts=records, scan_id=scan.id, aggregation_type=mode
        )
        persist_duplicate_findings(
            db, integration_id=integration.id, scan_id=scan.id, duplicate_details=duplicate_details
        )
        save_review_candidates(db, scan_id=scan.id, candidates=review_candidates)

        policy = get_policy_for_account_integration(db, integration.id)
        if policy is not None:
            identity_count = authoritative_identity_count(db, integration_id=policy.authoritative_integration_id)
            if identity_count > 0:
                detect_orphan_findings(db, scan_id=scan.id)

        total_duplicate_groups = sum(len(groups) for groups in duplicate_groups.values())
        total_duplicate_accounts = sum(
            int(group.get("duplicates", 0) or 0) for groups in duplicate_groups.values() for group in groups
        )
        return _complete_execution(
            db, execution=execution, source_file_name=connector_file.filename,
            source_path=connector_file.source_path, checksum=checksum,
            processed_count=len(records), inventory_stats=inventory_stats, scan_id=scan.id,
            duplicate_groups=total_duplicate_groups, duplicate_accounts=total_duplicate_accounts,
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
