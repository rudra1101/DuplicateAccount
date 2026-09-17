from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db_models.application import ApplicationRecord
from app.db_models.duplicate_finding import DuplicateFindingRecord
from app.db_models.source_account import SourceAccountRecord

AGGREGATION_TYPES = {"FULL", "DELTA"}


def normalize_aggregation_type(value: str | None) -> str:
    mode = str(value or "FULL").strip().upper()
    if mode not in AGGREGATION_TYPES:
        raise ValueError("Aggregation type must be FULL or DELTA.")
    return mode


def _payload(account: Any) -> dict[str, Any]:
    if hasattr(account, "model_dump"):
        return account.model_dump()
    if isinstance(account, dict):
        return dict(account)
    raise TypeError(f"Unsupported source account payload: {type(account).__name__}")


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fingerprint(raw: dict[str, Any]) -> str:
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _application_metadata(db: Session, integration_id: int) -> dict[str, tuple[int | None, int | None]]:
    rows = list(db.scalars(select(ApplicationRecord).options(selectinload(ApplicationRecord.schemas)).where(ApplicationRecord.integration_id == integration_id)).all())
    result: dict[str, tuple[int | None, int | None]] = {}
    for app in rows:
        active_schema = next((schema for schema in app.schemas if schema.is_active), None)
        result[app.name.strip().lower()] = (app.id, active_schema.id if active_schema else None)
    return result


def upsert_source_accounts(db: Session, *, integration_id: int, accounts: list[Any], scan_id: int | None, aggregation_type: str = "FULL") -> dict[str, int]:
    mode = normalize_aggregation_type(aggregation_type)
    now = datetime.now(UTC)
    app_meta = _application_metadata(db, integration_id)
    seen_keys: set[tuple[str, str]] = set()
    created = updated = unchanged = 0

    existing = list(db.scalars(select(SourceAccountRecord).where(SourceAccountRecord.integration_id == integration_id)).all())
    existing_by_key = {(item.application.strip().lower(), item.native_identity.strip().lower()): item for item in existing}

    for source in accounts:
        payload = _payload(source)
        raw = payload.get("rawAttributes") or payload.get("raw_attributes") or {}
        raw = dict(raw) if isinstance(raw, dict) else {}
        application = _clean(payload.get("application")) or "Unknown"
        native_identity = _clean(payload.get("id")) or _clean(payload.get("sourceAccountId")) or _clean(payload.get("source_account_id"))
        if not native_identity:
            native_identity = f"record-{_fingerprint(raw)[:24]}"

        key = (application.lower(), native_identity.lower())
        seen_keys.add(key)
        application_id, schema_id = app_meta.get(application.lower(), (None, None))
        fingerprint = _fingerprint(raw)
        record = existing_by_key.get(key)

        if record is None:
            record = SourceAccountRecord(
                integration_id=integration_id, application_id=application_id, schema_id=schema_id,
                application=application, native_identity=native_identity,
                display_name=_clean(payload.get("displayName") or payload.get("display_name")),
                username=_clean(payload.get("username")), email=_clean(payload.get("email")),
                employee_id=_clean(payload.get("employeeId") or payload.get("employee_id")), status=_clean(payload.get("status")),
                raw_attributes=raw, attribute_fingerprint=fingerprint, active=True, deleted=False,
                first_seen_at=now, last_seen_at=now, last_scan_id=scan_id, created_at=now, updated_at=now,
            )
            db.add(record)
            existing_by_key[key] = record
            created += 1
            continue

        changed = record.attribute_fingerprint != fingerprint or not record.active or record.deleted
        record.application_id = application_id
        record.schema_id = schema_id
        record.display_name = _clean(payload.get("displayName") or payload.get("display_name"))
        record.username = _clean(payload.get("username"))
        record.email = _clean(payload.get("email"))
        record.employee_id = _clean(payload.get("employeeId") or payload.get("employee_id"))
        record.status = _clean(payload.get("status"))
        record.raw_attributes = raw
        record.attribute_fingerprint = fingerprint
        record.active = True
        record.deleted = False
        record.last_seen_at = now
        record.last_scan_id = scan_id
        record.updated_at = now
        if changed:
            updated += 1
        else:
            unchanged += 1

    deleted = 0
    if mode == "FULL":
        for key, record in existing_by_key.items():
            if key not in seen_keys and (record.active or not record.deleted):
                record.active = False
                record.deleted = True
                record.updated_at = now
                deleted += 1

    db.commit()
    return {"created": created, "updated": updated, "unchanged": unchanged, "deleted": deleted, "total": len(seen_keys)}


def list_source_accounts(db: Session, *, integration_id: int, page: int = 1, page_size: int = 50, search: str = "", active: bool | None = None) -> tuple[list[SourceAccountRecord], int]:
    filters = [SourceAccountRecord.integration_id == integration_id]
    if active is not None:
        filters.append(SourceAccountRecord.active.is_(active))
    if search.strip():
        needle = f"%{search.strip()}%"
        filters.append(or_(SourceAccountRecord.native_identity.ilike(needle), SourceAccountRecord.username.ilike(needle), SourceAccountRecord.email.ilike(needle), SourceAccountRecord.employee_id.ilike(needle), SourceAccountRecord.display_name.ilike(needle), SourceAccountRecord.application.ilike(needle)))
    total = int(db.scalar(select(func.count(SourceAccountRecord.id)).where(and_(*filters))) or 0)
    rows = list(db.scalars(select(SourceAccountRecord).where(and_(*filters)).order_by(SourceAccountRecord.application.asc(), SourceAccountRecord.native_identity.asc()).offset((page - 1) * page_size).limit(page_size)).all())
    return rows, total


def source_account_to_dict(account: SourceAccountRecord) -> dict[str, Any]:
    return {
        "id": account.id, "integrationId": account.integration_id, "applicationId": account.application_id,
        "schemaId": account.schema_id, "application": account.application, "nativeIdentity": account.native_identity,
        "displayName": account.display_name, "username": account.username, "email": account.email,
        "employeeId": account.employee_id, "status": account.status, "rawAttributes": account.raw_attributes or {},
        "active": account.active, "deleted": account.deleted,
        "firstSeenAt": account.first_seen_at.isoformat() if account.first_seen_at else None,
        "lastSeenAt": account.last_seen_at.isoformat() if account.last_seen_at else None,
        "lastScanId": account.last_scan_id,
    }


def persist_duplicate_findings(db: Session, *, integration_id: int, scan_id: int, duplicate_details: dict[int, dict[str, Any]]) -> int:
    now = datetime.now(UTC)
    inventory = list(db.scalars(select(SourceAccountRecord).where(SourceAccountRecord.integration_id == integration_id)).all())
    by_key = {(item.application.strip().lower(), item.native_identity.strip().lower()): item for item in inventory}
    existing = list(db.scalars(select(DuplicateFindingRecord).where(DuplicateFindingRecord.integration_id == integration_id)).all())
    for finding in existing:
        finding.active = False
    existing_by_pair = {tuple(sorted((item.primary_source_account_id, item.duplicate_source_account_id))): item for item in existing}

    persisted = 0
    for detail in duplicate_details.values():
        primary = detail.get("primaryAccount") or {}
        primary_record = by_key.get((str(primary.get("application") or "").strip().lower(), str(primary.get("id") or "").strip().lower()))
        if primary_record is None:
            continue
        for candidate in detail.get("duplicates") or []:
            account = candidate.get("account") or {}
            duplicate_record = by_key.get((str(account.get("application") or "").strip().lower(), str(account.get("id") or "").strip().lower()))
            if duplicate_record is None or duplicate_record.id == primary_record.id:
                continue
            pair = tuple(sorted((primary_record.id, duplicate_record.id)))
            finding = existing_by_pair.get(pair)
            evidence = {
                "matchedAttributes": candidate.get("matchedAttributes") or [], "differentAttributes": candidate.get("differentAttributes") or [],
                "reasons": candidate.get("reasons") or [], "warnings": candidate.get("warnings") or [],
                "classification": candidate.get("classification"), "groupingEvidence": candidate.get("groupingEvidence"),
            }
            confidence = int(round(float(candidate.get("confidence") or 0)))
            if finding is None:
                finding = DuplicateFindingRecord(
                    integration_id=integration_id, primary_source_account_id=primary_record.id,
                    duplicate_source_account_id=duplicate_record.id, confidence=confidence, status="OPEN", active=True,
                    evidence=evidence, first_detected_at=now, last_detected_at=now, last_scan_id=scan_id,
                )
                db.add(finding)
                existing_by_pair[pair] = finding
            else:
                finding.confidence = confidence
                finding.active = True
                finding.evidence = evidence
                finding.last_detected_at = now
                finding.last_scan_id = scan_id
            persisted += 1
    db.commit()
    return persisted
