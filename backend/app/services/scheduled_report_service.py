from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.remediation_item import RemediationItemRecord
from app.db_models.report_email_template import ReportEmailTemplateRecord
from app.db_models.scan import ScanRecord
from app.db_models.scheduled_report import ScheduledReportConfigRecord, ScheduledReportRunRecord
from app.db_models.user import UserRecord
from app.services.email_service import send_email
from app.services.report_email_template_service import render_template, report_variables


ALLOWED_FREQUENCIES = {"WEEKLY", "MONTHLY", "QUARTERLY"}
DEFAULT_COLUMNS = [
    "groupId",
    "integration",
    "application",
    "primaryUsername",
    "candidateUsername",
    "confidence",
    "reviewDecision",
    "scanDate",
]
AVAILABLE_COLUMNS = [
    {"key": "groupId", "label": "Group ID"},
    {"key": "integration", "label": "Integration"},
    {"key": "application", "label": "Application"},
    {"key": "primaryUsername", "label": "Primary Username"},
    {"key": "candidateUsername", "label": "Candidate Username"},
    {"key": "confidence", "label": "Confidence"},
    {"key": "classification", "label": "Classification"},
    {"key": "recommendation", "label": "Recommendation"},
    {"key": "reviewDecision", "label": "Review Decision"},
    {"key": "reviewer", "label": "Reviewer"},
    {"key": "reviewedAt", "label": "Reviewed At"},
    {"key": "scanId", "label": "Scan ID"},
    {"key": "scanDate", "label": "Scan Date"},
]


def get_or_create_scheduled_report_config(db: Session) -> ScheduledReportConfigRecord:
    config = db.get(ScheduledReportConfigRecord, 1)
    if config is None:
        config = ScheduledReportConfigRecord(
            id=1,
            enabled=True,
            frequency="MONTHLY",
            include_admins=True,
            recipient_emails=[],
            selected_columns=list(DEFAULT_COLUMNS),
            email_template_id=None,
            timezone="Asia/Kolkata",
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def serialize_config(config: ScheduledReportConfigRecord) -> dict:
    return {
        "enabled": config.enabled,
        "frequency": config.frequency,
        "includeAdmins": config.include_admins,
        "recipientEmails": list(config.recipient_emails or []),
        "selectedColumns": list(config.selected_columns or DEFAULT_COLUMNS),
        "emailTemplateId": config.email_template_id,
        "availableColumns": AVAILABLE_COLUMNS,
        "timezone": config.timezone,
        "lastSentAt": config.last_sent_at.isoformat() if config.last_sent_at else None,
        "lastStatus": config.last_status,
        "lastError": config.last_error,
        "nextRunAt": config.next_run_at.isoformat() if config.next_run_at else None,
    }


def serialize_run(run: ScheduledReportRunRecord) -> dict:
    return {
        "id": run.id,
        "reportName": run.report_name,
        "filename": run.filename,
        "status": run.status,
        "testMode": run.test_mode,
        "recipients": list(run.recipients or []),
        "snapshot": dict(run.snapshot or {}),
        "rowCount": run.row_count,
        "errorMessage": run.error_message,
        "generatedAt": run.generated_at.isoformat() if run.generated_at else None,
    }


def list_scheduled_report_runs(db: Session, *, limit: int = 50) -> list[dict]:
    runs = db.scalars(
        select(ScheduledReportRunRecord)
        .order_by(ScheduledReportRunRecord.generated_at.desc(), ScheduledReportRunRecord.id.desc())
        .limit(max(1, min(limit, 200)))
    ).all()
    return [serialize_run(run) for run in runs]


def update_config(
    db: Session,
    *,
    enabled: bool,
    frequency: str,
    include_admins: bool,
    recipient_emails: list[str],
    selected_columns: list[str],
    email_template_id: int | None,
) -> ScheduledReportConfigRecord:
    normalized_frequency = frequency.strip().upper()
    if normalized_frequency not in ALLOWED_FREQUENCIES:
        raise ValueError("Frequency must be WEEKLY, MONTHLY, or QUARTERLY.")

    allowed = {item["key"] for item in AVAILABLE_COLUMNS}
    normalized_columns = [item for item in selected_columns if item in allowed]
    if not normalized_columns:
        normalized_columns = list(DEFAULT_COLUMNS)

    normalized_recipients = sorted(
        {item.strip().lower() for item in recipient_emails if item.strip()}
    )
    if enabled and not include_admins and not normalized_recipients:
        raise ValueError("At least one report recipient is required.")

    if email_template_id is not None:
        template = db.get(ReportEmailTemplateRecord, email_template_id)
        if template is None or not template.is_active:
            raise ValueError("Selected email template is not available.")

    config = get_or_create_scheduled_report_config(db)
    config.enabled = enabled
    config.frequency = normalized_frequency
    config.include_admins = include_admins
    config.recipient_emails = normalized_recipients
    config.selected_columns = normalized_columns
    config.email_template_id = email_template_id
    db.commit()
    db.refresh(config)
    return config


def executive_duplicate_snapshot(db: Session) -> dict:
    duplicate_groups = db.scalar(select(func.count(DuplicateGroupRecord.id))) or 0
    duplicate_candidates = db.scalar(select(func.count(DuplicateCandidateRecord.id))) or 0
    pending_review = db.scalar(
        select(func.count(DuplicateCandidateRecord.id)).where(
            DuplicateCandidateRecord.review_decision.is_(None)
        )
    ) or 0
    high_confidence_unresolved = db.scalar(
        select(func.count(DuplicateCandidateRecord.id)).where(
            DuplicateCandidateRecord.review_decision.is_(None),
            DuplicateCandidateRecord.confidence >= 95,
        )
    ) or 0
    confirmed_duplicates = db.scalar(select(func.count(RemediationItemRecord.id))) or 0
    awaiting_remediation = db.scalar(
        select(func.count(RemediationItemRecord.id)).where(
            RemediationItemRecord.status == "PENDING_ACTION"
        )
    ) or 0

    return {
        "duplicateGroups": int(duplicate_groups),
        "duplicateCandidates": int(duplicate_candidates),
        "pendingReview": int(pending_review),
        "confirmedDuplicates": int(confirmed_duplicates),
        "awaitingRemediation": int(awaiting_remediation),
        "highConfidenceUnresolved": int(high_confidence_unresolved),
        "generatedAt": datetime.utcnow().isoformat(),
    }


def _detail_rows(db: Session) -> list[dict]:
    statement = (
        select(DuplicateCandidateRecord, DuplicateGroupRecord, ScanRecord, IntegrationRecord)
        .join(DuplicateGroupRecord, DuplicateGroupRecord.id == DuplicateCandidateRecord.group_id)
        .join(ScanRecord, ScanRecord.id == DuplicateGroupRecord.scan_id)
        .outerjoin(IntegrationRecord, IntegrationRecord.id == ScanRecord.integration_id)
        .where(DuplicateCandidateRecord.review_decision.is_(None))
        .order_by(DuplicateCandidateRecord.confidence.desc(), DuplicateCandidateRecord.id.desc())
    )
    rows = []
    for candidate, group, scan, integration in db.execute(statement).all():
        rows.append({
            "groupId": group.id,
            "integration": integration.name if integration else None,
            "application": group.application,
            "primaryUsername": group.primary_username,
            "candidateUsername": candidate.username,
            "confidence": candidate.confidence,
            "classification": candidate.classification,
            "recommendation": candidate.recommendation,
            "reviewDecision": candidate.review_decision or "PENDING",
            "reviewer": candidate.reviewer_name,
            "reviewedAt": candidate.reviewed_at.isoformat() if candidate.reviewed_at else None,
            "scanId": scan.id,
            "scanDate": scan.created_at.isoformat() if scan.created_at else None,
        })
    return rows


def _csv_for_columns(rows: list[dict], columns: list[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column) for column in columns})
    return output.getvalue()


def resolve_recipients(db: Session, config: ScheduledReportConfigRecord) -> list[str]:
    recipients = set(config.recipient_emails or [])
    if config.include_admins:
        admin_emails = db.scalars(
            select(UserRecord.email).where(
                UserRecord.is_active.is_(True),
                UserRecord.role.in_(["ADMIN", "OWNER"]),
            )
        ).all()
        recipients.update(email for email in admin_emails if email)
    return sorted(recipients)


def _default_email(snapshot: dict, *, test_mode: bool) -> tuple[str, str, str]:
    prefix = "TEST - " if test_mode else ""
    subject = f"{prefix}IdentityAI Duplicate Risk Report"
    text_body = (
        "IdentityAI Duplicate Risk Report\n\n"
        f"Duplicate groups detected: {snapshot['duplicateGroups']}\n"
        f"Duplicate candidate accounts: {snapshot['duplicateCandidates']}\n"
        f"Pending review: {snapshot['pendingReview']}\n"
        f"Confirmed duplicates: {snapshot['confirmedDuplicates']}\n"
        f"Confirmed duplicates awaiting remediation: {snapshot['awaitingRemediation']}\n"
        f"High-confidence unresolved candidates (>=95%): {snapshot['highConfidenceUnresolved']}\n\n"
        "A CSV containing the current unresolved duplicate candidates is attached."
    )
    html_body = f"""
    <h2>IdentityAI Duplicate Risk Report</h2>
    <table cellpadding="8" cellspacing="0" border="1">
      <tr><td>Duplicate groups detected</td><td><strong>{snapshot['duplicateGroups']}</strong></td></tr>
      <tr><td>Duplicate candidate accounts</td><td><strong>{snapshot['duplicateCandidates']}</strong></td></tr>
      <tr><td>Pending review</td><td><strong>{snapshot['pendingReview']}</strong></td></tr>
      <tr><td>Confirmed duplicates</td><td><strong>{snapshot['confirmedDuplicates']}</strong></td></tr>
      <tr><td>Confirmed duplicates awaiting remediation</td><td><strong>{snapshot['awaitingRemediation']}</strong></td></tr>
      <tr><td>High-confidence unresolved candidates (&gt;=95%)</td><td><strong>{snapshot['highConfidenceUnresolved']}</strong></td></tr>
    </table>
    <p>A CSV containing the current unresolved duplicate candidates is attached.</p>
    """
    return subject, text_body, html_body


def send_scheduled_duplicate_report(db: Session, *, test_mode: bool = False) -> dict:
    config = get_or_create_scheduled_report_config(db)
    recipients = resolve_recipients(db, config)
    snapshot = executive_duplicate_snapshot(db)
    columns = list(config.selected_columns or DEFAULT_COLUMNS)
    rows = _detail_rows(db)
    csv_content = _csv_for_columns(rows, columns)
    generated_at = datetime.utcnow()
    filename = f"duplicate_risk_report_{generated_at.strftime('%Y%m%d_%H%M%S')}.csv"

    run = ScheduledReportRunRecord(
        report_name="Executive Duplicate Risk Report",
        filename=filename,
        status="GENERATED",
        test_mode=test_mode,
        recipients=recipients,
        snapshot=snapshot,
        row_count=len(rows),
        csv_content=csv_content,
        generated_at=generated_at,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    template = (
        db.get(ReportEmailTemplateRecord, config.email_template_id)
        if config.email_template_id is not None
        else None
    )
    if template is not None and template.is_active:
        variables = report_variables(
            snapshot=snapshot,
            generated_at=generated_at,
            unresolved_rows=len(rows),
            recipient_count=len(recipients),
            test_mode=test_mode,
        )
        subject = render_template(template.subject_template, variables) or ""
        text_body = render_template(template.text_body_template, variables) or ""
        html_body = render_template(template.html_body_template, variables)
    else:
        subject, text_body, html_body = _default_email(snapshot, test_mode=test_mode)

    try:
        send_email(
            recipients=recipients,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            attachment_name=filename,
            attachment_content=csv_content,
        )
        run.status = "SENT"
        run.error_message = None
        if not test_mode:
            config.last_sent_at = generated_at
        config.last_status = "SENT"
        config.last_error = None
        db.commit()
    except Exception as exc:
        run.status = "EMAIL_FAILED"
        run.error_message = str(exc)
        config.last_status = "FAILED"
        config.last_error = str(exc)
        db.commit()
        raise

    return {
        "run": serialize_run(run),
        "recipients": recipients,
        "snapshot": snapshot,
        "unresolvedRows": len(rows),
        "status": "SENT",
    }
