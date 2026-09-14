from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db_models.identity import IdentityRecord


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


def replace_authoritative_identities(
    db: Session,
    *,
    integration_id: int,
    identities: list[Any],
) -> int:
    """Replace the current identity population for one authoritative integration.

    Authoritative ingestion is schema-driven: no customer-specific field is required.
    Known canonical values are populated when available, while the complete source row
    is always preserved in raw_attributes for configured correlation rules.
    """
    db.execute(delete(IdentityRecord).where(IdentityRecord.integration_id == integration_id))

    count = 0
    for position, source in enumerate(identities, start=1):
        payload = _account_payload(source)
        raw = payload.get("rawAttributes") or payload.get("raw_attributes") or {}
        raw_dict = dict(raw) if isinstance(raw, dict) else {}

        source_identity_id = _value(payload, "id", "sourceIdentityId")
        employee_id = _value(payload, "employeeId", "employee_id")
        email = _value(payload, "email")
        username = _value(payload, "username")

        # Never discard an authoritative row solely because it does not expose one
        # of our familiar canonical fields. A deterministic internal key is enough
        # for persistence; correlation still evaluates the original raw attributes.
        source_identity_id = (
            source_identity_id
            or employee_id
            or email
            or username
            or _stable_identity_key(raw_dict or payload, position)
        )

        db.add(
            IdentityRecord(
                integration_id=integration_id,
                source_identity_id=source_identity_id,
                employee_id=employee_id,
                username=username,
                email=email,
                display_name=_value(payload, "displayName", "display_name"),
                department=_value(payload, "department"),
                manager=_value(payload, "manager"),
                employment_status=_value(payload, "status", "employmentStatus", "employment_status"),
                raw_attributes=raw_dict,
            )
        )
        count += 1

    db.commit()
    return count


def authoritative_identity_count(db: Session, integration_id: int | None = None) -> int:
    statement = select(func.count(IdentityRecord.id))
    if integration_id is not None:
        statement = statement.where(IdentityRecord.integration_id == integration_id)
    return int(db.scalar(statement) or 0)
