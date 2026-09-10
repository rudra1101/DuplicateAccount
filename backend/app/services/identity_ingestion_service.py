from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
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


def replace_authoritative_identities(
    db: Session,
    *,
    integration_id: int,
    identities: list[Any],
) -> int:
    """Replace the current identity population for one authoritative integration.

    A connector execution represents a point-in-time authoritative snapshot. Replacing
    the integration's prior rows avoids retaining workers who disappeared from HR.
    """
    db.execute(delete(IdentityRecord).where(IdentityRecord.integration_id == integration_id))

    count = 0
    for source in identities:
        payload = _account_payload(source)
        raw = payload.get("rawAttributes") or payload.get("raw_attributes") or {}

        source_identity_id = _value(payload, "id", "sourceIdentityId")
        employee_id = _value(payload, "employeeId", "employee_id")
        email = _value(payload, "email")
        username = _value(payload, "username")
        source_identity_id = source_identity_id or employee_id or email or username
        if not source_identity_id:
            continue

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
                raw_attributes=dict(raw) if isinstance(raw, dict) else {},
            )
        )
        count += 1

    db.commit()
    return count


def authoritative_identity_count(db: Session) -> int:
    return len(list(db.scalars(select(IdentityRecord.id)).all()))
