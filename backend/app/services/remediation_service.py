from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_models.integration import IntegrationRecord
from app.db_models.remediation_item import RemediationItemRecord
from app.db_models.review_decision_history import ReviewDecisionHistoryRecord
from app.services.review_pair_feedback_service import normalize_pair_keys, upsert_pair_feedback


VALID_REMEDIATION_STATUSES = {
    "PENDING_ACTION",
    "TICKET_OPEN",
    "ACTIONED",
    "IGNORED",
    "FAILED",
}
VALID_REMEDIATION_ACTIONS = {"DISABLE", "DELETE"}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def record_review_decision(
    db: Session,
    *,
    integration_id: int,
    application: str,
    account_1_key: str,
    account_2_key: str,
    decision: str,
    confidence: float | None = None,
    reviewer_name: str | None = None,
    comment: str | None = None,
    source: str = "REVIEW",
    account_1_data: dict[str, Any] | None = None,
    account_2_data: dict[str, Any] | None = None,
) -> None:
    key_1, key_2 = normalize_pair_keys(account_1_key, account_2_key)
    data_1 = account_1_data or {}
    data_2 = account_2_data or {}
    if key_1 != str(account_1_key):
        data_1, data_2 = data_2, data_1

    normalized_decision = decision.strip().upper()
    db.add(
        ReviewDecisionHistoryRecord(
            integration_id=integration_id,
            application=application,
            account_1_key=key_1,
            account_2_key=key_2,
            decision=normalized_decision,
            confidence=confidence,
            reviewer_name=(reviewer_name or "").strip() or None,
            comment=(comment or "").strip() or None,
            source=source,
            account_1_data=data_1,
            account_2_data=data_2,
        )
    )

    existing = db.scalar(
        select(RemediationItemRecord).where(
            RemediationItemRecord.integration_id == integration_id,
            RemediationItemRecord.application == application,
            RemediationItemRecord.account_1_key == key_1,
            RemediationItemRecord.account_2_key == key_2,
        )
    )

    if normalized_decision == "DUPLICATE":
        if existing is None:
            existing = RemediationItemRecord(
                integration_id=integration_id,
                application=application,
                account_1_key=key_1,
                account_2_key=key_2,
                status="PENDING_ACTION",
            )
            db.add(existing)
        elif existing.status in {"IGNORED", "FAILED"} and not existing.service_desk_ticket_id:
            existing.status = "PENDING_ACTION"

        existing.account_1_data = data_1
        existing.account_2_data = data_2
        existing.confidence = confidence
        existing.reviewer_name = (reviewer_name or "").strip() or None
        existing.review_comment = (comment or "").strip() or None
        existing.updated_at = _utc_now()
    elif existing is not None and normalized_decision in {"NOT_DUPLICATE", "UNCERTAIN"}:
        existing.status = "IGNORED"
        existing.action_comment = f"Removed from active remediation after reviewer decision: {normalized_decision}."
        existing.updated_at = _utc_now()


def _serialize_remediation(record: RemediationItemRecord, integration_name: str | None = None) -> dict[str, Any]:
    return {
        "id": record.id,
        "integrationId": record.integration_id,
        "integrationName": integration_name,
        "application": record.application,
        "account1Key": record.account_1_key,
        "account2Key": record.account_2_key,
        "account1": record.account_1_data or {},
        "account2": record.account_2_data or {},
        "confidence": record.confidence,
        "reviewerName": record.reviewer_name,
        "reviewComment": record.review_comment,
        "status": record.status,
        "actionComment": record.action_comment,
        "actionedBy": record.actioned_by,
        "remediationAction": record.remediation_action,
        "targetAccountKey": record.target_account_key,
        "ticketId": record.service_desk_ticket_id,
        "ticketStatus": record.service_desk_ticket_status,
        "ticketUrl": record.service_desk_ticket_url,
        "ticketCreatedAt": record.ticket_created_at.isoformat() if record.ticket_created_at else None,
        "ticketLastSyncedAt": record.ticket_last_synced_at.isoformat() if record.ticket_last_synced_at else None,
        "ticketError": record.ticket_error,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
        "updatedAt": record.updated_at.isoformat() if record.updated_at else None,
    }


def list_remediation_items(
    db: Session,
    *,
    status: str | None = None,
    integration_id: int | None = None,
    application: str | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
    remediation_action: str | None = None,
    ticket_status: str | None = None,
    has_ticket: bool | None = None,
) -> list[dict[str, Any]]:
    if min_confidence is not None and max_confidence is not None and min_confidence > max_confidence:
        raise ValueError("Minimum confidence cannot be greater than maximum confidence.")

    query = select(RemediationItemRecord)
    if status:
        normalized = status.strip().upper()
        if normalized not in VALID_REMEDIATION_STATUSES:
            raise ValueError("Invalid remediation status.")
        query = query.where(RemediationItemRecord.status == normalized)
    if integration_id is not None:
        query = query.where(RemediationItemRecord.integration_id == integration_id)
    if application:
        application_value = application.strip().lower()
        if application_value:
            query = query.where(func.lower(RemediationItemRecord.application).contains(application_value))
    if min_confidence is not None:
        query = query.where(RemediationItemRecord.confidence >= min_confidence)
    if max_confidence is not None:
        query = query.where(RemediationItemRecord.confidence <= max_confidence)
    if remediation_action:
        normalized_action = remediation_action.strip().upper()
        if normalized_action not in VALID_REMEDIATION_ACTIONS:
            raise ValueError("Invalid remediation action.")
        query = query.where(RemediationItemRecord.remediation_action == normalized_action)
    if ticket_status:
        ticket_status_value = ticket_status.strip().lower()
        if ticket_status_value:
            query = query.where(
                func.lower(RemediationItemRecord.service_desk_ticket_status).contains(ticket_status_value)
            )
    if has_ticket is True:
        query = query.where(RemediationItemRecord.service_desk_ticket_id.is_not(None))
    elif has_ticket is False:
        query = query.where(RemediationItemRecord.service_desk_ticket_id.is_(None))

    records = list(
        db.scalars(
            query.order_by(RemediationItemRecord.updated_at.desc(), RemediationItemRecord.id.desc())
        ).all()
    )
    integration_ids = {record.integration_id for record in records}
    names = {
        row.id: row.name
        for row in db.execute(
            select(IntegrationRecord.id, IntegrationRecord.name).where(
                IntegrationRecord.id.in_(integration_ids)
            )
        ).all()
    } if integration_ids else {}

    return [_serialize_remediation(record, names.get(record.integration_id)) for record in records]


def list_decision_history(db: Session, *, limit: int = 200) -> list[dict[str, Any]]:
    records = list(
        db.scalars(
            select(ReviewDecisionHistoryRecord)
            .order_by(ReviewDecisionHistoryRecord.created_at.desc(), ReviewDecisionHistoryRecord.id.desc())
            .limit(limit)
        ).all()
    )
    return [
        {
            "id": record.id,
            "integrationId": record.integration_id,
            "application": record.application,
            "account1Key": record.account_1_key,
            "account2Key": record.account_2_key,
            "decision": record.decision,
            "confidence": record.confidence,
            "reviewerName": record.reviewer_name,
            "comment": record.comment,
            "source": record.source,
            "account1": record.account_1_data or {},
            "account2": record.account_2_data or {},
            "createdAt": record.created_at.isoformat() if record.created_at else None,
        }
        for record in records
    ]


def update_remediation_status(
    db: Session,
    *,
    item_id: int,
    status: str,
    action_comment: str | None = None,
    actioned_by: str | None = None,
) -> dict[str, Any]:
    record = db.get(RemediationItemRecord, item_id)
    if record is None:
        raise ValueError("Remediation item not found.")
    normalized = status.strip().upper()
    if normalized not in VALID_REMEDIATION_STATUSES:
        raise ValueError("Invalid remediation status.")
    if record.status == "TICKET_OPEN" and normalized == "ACTIONED":
        raise ValueError("Ticket-driven remediation is completed only when the Service Desk ticket reaches a configured completed status.")

    if normalized == "IGNORED":
        if record.service_desk_ticket_id:
            raise ValueError("A remediation item with an existing Service Desk ticket cannot be returned to Review Queue by Ignore.")

        # IGNORE in Remediation means "send this pair back for review", not a
        # durable NOT_DUPLICATE decision. Passing UNCERTAIN removes any durable
        # DUPLICATE/NOT_DUPLICATE feedback for the pair so future scans can
        # surface it for human review again.
        upsert_pair_feedback(
            db,
            integration_id=record.integration_id,
            application=record.application,
            account_1_key=record.account_1_key,
            account_2_key=record.account_2_key,
            decision="UNCERTAIN",
            comment="Returned to Review Queue from Remediation.",
            reviewer_name=(actioned_by or "").strip() or None,
        )
        record.action_comment = (
            (action_comment or "").strip()
            or "Ignored in Remediation and returned to Review Queue for another decision."
        )
    else:
        record.action_comment = (action_comment or "").strip() or None

    record.status = normalized
    record.actioned_by = (actioned_by or "").strip() or None
    record.updated_at = _utc_now()
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "status": record.status,
        "actionComment": record.action_comment,
        "actionedBy": record.actioned_by,
        "updatedAt": record.updated_at.isoformat() if record.updated_at else None,
    }