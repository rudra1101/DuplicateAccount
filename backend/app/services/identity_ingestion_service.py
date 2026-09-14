from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_models.identity import IdentityRecord
from app.services.source_account_inventory_service import normalize_aggregation_type


ACTIVE_IDENTITY_STATUSES = {"active", "enabled", "true", "1", "yes"}


def _value(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _account_payload(account: Any) -> dict[str, Any]:
    if hasattr(account, "model_dump"):
        return account.model_dump()
    if isinstance(account, dict):
        return dict(account)
    raise TypeError(f"Unsupported identity payload: {type(account).__name__}")


def _stable_identity_key(raw: dict[str, Any], position: int) -> str:
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return f"identity-{position}-{digest}"


def upsert_authoritative_identities(
    db: Session,
    *,
    integration_id: int,
    identities: list[Any],
    aggregation_type: str = "FULL",
) -> dict[str, int]:
    """Reconcile the current authoritative identity population.

    FULL treats the incoming population as a complete snapshot and marks missing
    identities inactive/deleted. DELTA changes only identities present in the batch.
    Existing rows are updated in place so identity IDs remain stable for references.
    """
    mode = normalize_aggregation_type(aggregation_type)
    now = datetime.now(UTC)
    existing = list(
        db.scalars(
            select(IdentityRecord).where(IdentityRecord.integration_id == integration_id)
        ).all()
    )
    existing_by_key = {
        item.source_identity_id.strip().lower(): item
        for item in existing
    }
    seen_keys: set[str] = set()
    created = updated = unchanged = 0

    for position, source in enumerate(identities, start=1):
        payload = _account_payload(source)
        raw = payload.get("rawAttributes") or payload.get("raw_attributes") or {}
        raw_dict = dict(raw) if isinstance(raw, dict) else {}

        employee_id = _value(payload, "employeeId", "employee_id")
        email = _value(payload, "email")
        username = _value(payload, "username")
        source_identity_id = (
            _value(payload, "id", "sourceIdentityId")
            or employee_id
            or email
            or username
            or _stable_identity_key(raw_dict or payload, position)
        )
        key = source_identity_id.lower()
        seen_keys.add(key)

        values = {
            "employee_id": employee_id,
            "username": username,
            "email": email,
            "display_name": _value(payload, "displayName", "display_name"),
            "department": _value(payload, "department"),
            "manager": _value(payload, "manager"),
            "employment_status": _value(payload, "status", "employmentStatus", "employment_status"),
            "raw_attributes": raw_dict,
        }
        record = existing_by_key.get(key)

        if record is None:
            record = IdentityRecord(
                integration_id=integration_id,
                source_identity_id=source_identity_id,
                **values,
                active=True,
                deleted=False,
                first_seen_at=now,
                last_seen_at=now,
            )
            db.add(record)
            existing_by_key[key] = record
            created += 1
            continue

        changed = (
            any(getattr(record, field) != value for field, value in values.items())
            or not record.active
            or record.deleted
        )
        for field, value in values.items():
            setattr(record, field, value)
        record.active = True
        record.deleted = False
        record.last_seen_at = now
        record.updated_at = now
        if changed:
            updated += 1
        else:
            unchanged += 1

    deleted = 0
    if mode == "FULL":
        for key, record in existing_by_key.items():
            if key in seen_keys:
                continue
            if record.active or not record.deleted:
                record.active = False
                record.deleted = True
                record.updated_at = now
                deleted += 1

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "deleted": deleted,
        "total": len(seen_keys),
    }


def replace_authoritative_identities(
    db: Session,
    *,
    integration_id: int,
    identities: list[Any],
) -> int:
    """Backward-compatible FULL reconciliation wrapper."""
    stats = upsert_authoritative_identities(
        db,
        integration_id=integration_id,
        identities=identities,
        aggregation_type="FULL",
    )
    return stats["total"]


def authoritative_identity_count(db: Session, integration_id: int | None = None) -> int:
    statement = select(func.count(IdentityRecord.id)).where(
        IdentityRecord.active.is_(True),
        IdentityRecord.deleted.is_(False),
    )
    if integration_id is not None:
        statement = statement.where(IdentityRecord.integration_id == integration_id)
    return int(db.scalar(statement) or 0)
