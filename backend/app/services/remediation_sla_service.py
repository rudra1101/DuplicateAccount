from __future__ import annotations

from datetime import UTC, datetime, timedelta

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.db_models.remediation_item import RemediationItemRecord
from app.services.email_service import send_email
from app.services.settings_service import get_application_settings, get_or_create_application_settings


ACTIVE_SLA_STATUSES = {"PENDING_ACTION", "TICKET_OPEN", "FAILED"}
VALID_SLA_FILTERS = {"ON_TRACK", "WARNING", "OVERDUE", "ESCALATED"}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _emails_from_text(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def remediation_sla_settings_response(db: Session) -> dict:
    settings = get_application_settings(db)
    return {
        "enabled": bool(settings and settings.remediation_sla_enabled),
        "slaHours": int(settings.remediation_sla_hours if settings else 72),
        "warningHours": int(settings.remediation_warning_hours if settings else 24),
        "autoEscalate": bool(settings.remediation_auto_escalate if settings else True),
        "escalationEmails": _emails_from_text(settings.remediation_escalation_emails if settings else ""),
    }


def update_remediation_sla_settings(
    db: Session,
    *,
    enabled: bool,
    sla_hours: int,
    warning_hours: int,
    auto_escalate: bool,
    escalation_emails: list[str],
):
    if sla_hours < 1 or sla_hours > 24 * 365:
        raise ValueError("Remediation SLA must be between 1 hour and 365 days.")
    if warning_hours < 0 or warning_hours >= sla_hours:
        raise ValueError("Warning threshold must be zero or greater and less than the SLA duration.")

    cleaned_emails: list[str] = []
    for raw in escalation_emails:
        value = raw.strip()
        if not value:
            continue
        try:
            cleaned_emails.append(validate_email(value, check_deliverability=False).normalized)
        except EmailNotValidError as exc:
            raise ValueError(f"Invalid escalation email address: {value}") from exc

    settings = get_or_create_application_settings(db)
    was_enabled = bool(settings.remediation_sla_enabled)
    settings.remediation_sla_enabled = enabled
    settings.remediation_sla_hours = sla_hours
    settings.remediation_warning_hours = warning_hours
    settings.remediation_auto_escalate = auto_escalate
    settings.remediation_escalation_emails = ",".join(dict.fromkeys(cleaned_emails))

    if enabled:
        active_records = list(
            db.scalars(
                select(RemediationItemRecord).where(
                    RemediationItemRecord.status.in_(ACTIVE_SLA_STATUSES)
                )
            ).all()
        )
        now = _utc_now()
        for record in active_records:
            if record.sla_due_at is None or not was_enabled:
                record.sla_due_at = now + timedelta(hours=sla_hours)
                record.sla_escalated_at = None
                record.sla_notification_sent_at = None

    db.commit()
    db.refresh(settings)
    return settings


def assign_due_at(db: Session, record: RemediationItemRecord, *, reset: bool = False) -> None:
    settings = get_application_settings(db)
    if not settings or not settings.remediation_sla_enabled:
        if reset:
            record.sla_due_at = None
            record.sla_escalated_at = None
            record.sla_notification_sent_at = None
        return
    if record.sla_due_at is None or reset:
        record.sla_due_at = _utc_now() + timedelta(hours=int(settings.remediation_sla_hours))
        if reset:
            record.sla_escalated_at = None
            record.sla_notification_sent_at = None


def calculate_sla_state(
    record: RemediationItemRecord,
    *,
    warning_hours: int,
    enabled: bool,
    now: datetime | None = None,
) -> str:
    if not enabled or record.status not in ACTIVE_SLA_STATUSES:
        return "NONE"
    due_at = _as_utc(record.sla_due_at)
    if due_at is None:
        return "NONE"
    if record.sla_escalated_at is not None:
        return "ESCALATED"
    current = now or _utc_now()
    if current >= due_at:
        return "OVERDUE"
    if current >= due_at - timedelta(hours=warning_hours):
        return "WARNING"
    return "ON_TRACK"


def serialize_sla(record: RemediationItemRecord, *, enabled: bool, warning_hours: int) -> dict:
    due_at = _as_utc(record.sla_due_at)
    now = _utc_now()
    seconds_remaining = int((due_at - now).total_seconds()) if due_at else None
    return {
        "slaStatus": calculate_sla_state(
            record,
            warning_hours=warning_hours,
            enabled=enabled,
            now=now,
        ),
        "slaDueAt": due_at.isoformat() if due_at else None,
        "slaEscalatedAt": _as_utc(record.sla_escalated_at).isoformat() if record.sla_escalated_at else None,
        "slaNotificationSentAt": _as_utc(record.sla_notification_sent_at).isoformat() if record.sla_notification_sent_at else None,
        "slaSecondsRemaining": seconds_remaining,
    }


def process_remediation_sla() -> None:
    with SessionLocal() as db:
        settings = get_application_settings(db)
        if not settings or not settings.remediation_sla_enabled or not settings.remediation_auto_escalate:
            return

        now = _utc_now()
        records = list(
            db.scalars(
                select(RemediationItemRecord).where(
                    RemediationItemRecord.status.in_(ACTIVE_SLA_STATUSES),
                    RemediationItemRecord.sla_due_at.is_not(None),
                    RemediationItemRecord.sla_due_at <= now,
                    RemediationItemRecord.sla_escalated_at.is_(None),
                )
            ).all()
        )
        if not records:
            return

        recipients = _emails_from_text(settings.remediation_escalation_emails)
        for record in records:
            record.sla_escalated_at = now

        db.commit()

        if not recipients:
            return

        for record in records:
            try:
                send_email(
                    recipients=recipients,
                    subject=f"IdentityAI remediation SLA breached: {record.application}",
                    text_body=(
                        "A duplicate-account remediation item has breached its SLA.\n\n"
                        f"Application: {record.application}\n"
                        f"Remediation item: {record.id}\n"
                        f"Confidence: {record.confidence if record.confidence is not None else 'N/A'}\n"
                        f"Status: {record.status}\n"
                        f"Ticket: {record.service_desk_ticket_id or 'Not created'}\n"
                        f"Due at: {_as_utc(record.sla_due_at).isoformat() if record.sla_due_at else 'N/A'}\n"
                    ),
                )
                record.sla_notification_sent_at = _utc_now()
                db.commit()
            except Exception:
                db.rollback()
