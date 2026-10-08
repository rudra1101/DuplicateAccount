from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db_models.identity import IdentityRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.orphan_state import OrphanStateRecord
from app.db_models.source_account import SourceAccountRecord


ORPHAN_TYPES = {
    "UNMATCHED_ACCOUNT",
    "AMBIGUOUS_CORRELATION",
    "TERMINATED_IDENTITY",
}


def _date_start(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.combine(datetime.fromisoformat(value).date(), time.min)


def _date_end(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.combine(datetime.fromisoformat(value).date(), time.max)


def _contains(value: str) -> str:
    return f"%{value.strip()}%"


def _identity_summary(identity: IdentityRecord | None) -> dict[str, Any] | None:
    if identity is None:
        return None
    return {
        "id": identity.id,
        "sourceIdentityId": identity.source_identity_id,
        "displayName": identity.display_name,
        "username": identity.username,
        "email": identity.email,
        "employeeId": identity.employee_id,
        "employmentStatus": identity.employment_status,
    }


def list_orphan_accounts(
    db: Session,
    *,
    integration_id: int | None = None,
    integration_name: str | None = None,
    application: str | None = None,
    orphan_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    reason: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return current orphan accounts using the same persisted orphan state as the UI.

    The query is deliberately service-level so Rudrix and report generation share one
    source of truth rather than implementing separate orphan semantics.
    """

    statement = (
        select(OrphanStateRecord, SourceAccountRecord, IntegrationRecord)
        .join(
            SourceAccountRecord,
            SourceAccountRecord.id == OrphanStateRecord.source_account_id,
        )
        .join(
            IntegrationRecord,
            IntegrationRecord.id == OrphanStateRecord.integration_id,
        )
        .where(
            OrphanStateRecord.active.is_(True),
            SourceAccountRecord.active.is_(True),
        )
    )

    conditions = []
    if integration_id is not None:
        conditions.append(OrphanStateRecord.integration_id == int(integration_id))
    if integration_name:
        conditions.append(IntegrationRecord.name.ilike(_contains(integration_name)))
    if application:
        conditions.append(SourceAccountRecord.application.ilike(_contains(application)))
    if orphan_type:
        conditions.append(OrphanStateRecord.orphan_type == orphan_type.strip().upper())
    if status:
        conditions.append(OrphanStateRecord.status == status.strip().upper())

    if search:
        term = _contains(search)
        conditions.append(
            or_(
                SourceAccountRecord.native_identity.ilike(term),
                SourceAccountRecord.username.ilike(term),
                SourceAccountRecord.email.ilike(term),
                SourceAccountRecord.employee_id.ilike(term),
                SourceAccountRecord.display_name.ilike(term),
            )
        )

    start = _date_start(date_from)
    end = _date_end(date_to)
    if start is not None:
        conditions.append(OrphanStateRecord.first_detected_at >= start)
    if end is not None:
        conditions.append(OrphanStateRecord.first_detected_at <= end)
    if conditions:
        statement = statement.where(and_(*conditions))

    statement = statement.order_by(
        OrphanStateRecord.last_detected_at.desc(),
        SourceAccountRecord.id.desc(),
    )

    rows = list(db.execute(statement).all())

    if reason:
        reason_needle = reason.casefold().strip()
        rows = [
            row
            for row in rows
            if reason_needle
            in str((row[0].evidence or {}).get("reason") or "").casefold()
        ]

    if limit is not None:
        rows = rows[: max(1, int(limit))]

    identity_ids = sorted(
        {
            orphan.matched_identity_id
            for orphan, _account, _integration in rows
            if orphan.matched_identity_id is not None
        }
    )
    identities = (
        list(
            db.scalars(
                select(IdentityRecord).where(IdentityRecord.id.in_(identity_ids))
            ).all()
        )
        if identity_ids
        else []
    )
    identity_by_id = {identity.id: identity for identity in identities}

    results: list[dict[str, Any]] = []
    for orphan, account, integration in rows:
        evidence = dict(orphan.evidence or {})
        results.append(
            {
                "orphanStateId": orphan.id,
                "sourceAccountId": account.id,
                "integrationId": orphan.integration_id,
                "integrationName": integration.name,
                "application": account.application,
                "nativeIdentity": account.native_identity,
                "username": account.username,
                "displayName": account.display_name,
                "email": account.email,
                "employeeId": account.employee_id,
                "accountStatus": account.status,
                "orphaned": True,
                "orphanType": orphan.orphan_type,
                "orphanStatus": orphan.status,
                "correlationMethod": orphan.correlation_method,
                "reason": evidence.get("reason"),
                "policyId": evidence.get("policyId"),
                "policyName": evidence.get("policyName"),
                "strategy": evidence.get("strategy"),
                "correlationAttempts": evidence.get("correlationAttempts") or [],
                "matchedIdentity": _identity_summary(
                    identity_by_id.get(orphan.matched_identity_id)
                    if orphan.matched_identity_id is not None
                    else None
                ),
                "firstDetectedAt": orphan.first_detected_at.isoformat(),
                "lastDetectedAt": orphan.last_detected_at.isoformat(),
                "lastSeenAt": account.last_seen_at.isoformat() if account.last_seen_at else None,
            }
        )

    return results
