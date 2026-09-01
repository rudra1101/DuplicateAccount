from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.report_email_template import ReportEmailTemplateRecord
from app.db_models.scheduled_report import ScheduledReportConfigRecord


VARIABLES = [
    "report_name",
    "generated_at",
    "duplicate_groups",
    "duplicate_candidates",
    "pending_review",
    "confirmed_duplicates",
    "awaiting_remediation",
    "high_confidence_unresolved",
    "unresolved_rows",
    "recipient_count",
    "test_prefix",
]
_VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def serialize_template(template: ReportEmailTemplateRecord) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "subjectTemplate": template.subject_template,
        "textBodyTemplate": template.text_body_template,
        "htmlBodyTemplate": template.html_body_template or "",
        "isActive": template.is_active,
        "createdAt": template.created_at.isoformat() if template.created_at else None,
        "updatedAt": template.updated_at.isoformat() if template.updated_at else None,
    }


def list_templates(db: Session, *, active_only: bool = False) -> list[ReportEmailTemplateRecord]:
    statement = select(ReportEmailTemplateRecord).order_by(
        ReportEmailTemplateRecord.name.asc(),
        ReportEmailTemplateRecord.id.asc(),
    )
    if active_only:
        statement = statement.where(ReportEmailTemplateRecord.is_active.is_(True))
    return list(db.scalars(statement).all())


def _validate_content(subject: str, text_body: str, html_body: str | None) -> None:
    if not subject.strip():
        raise ValueError("Template subject is required.")
    if not text_body.strip():
        raise ValueError("Plain-text email body is required.")

    supported = set(VARIABLES)
    used = set()
    for content in (subject, text_body, html_body or ""):
        used.update(_VARIABLE_PATTERN.findall(content))
    unsupported = sorted(used - supported)
    if unsupported:
        raise ValueError(
            "Unsupported template variable(s): " + ", ".join(unsupported)
        )


def create_template(
    db: Session,
    *,
    name: str,
    subject_template: str,
    text_body_template: str,
    html_body_template: str | None,
    is_active: bool,
) -> ReportEmailTemplateRecord:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Template name is required.")
    existing = db.scalar(
        select(ReportEmailTemplateRecord).where(
            ReportEmailTemplateRecord.name == normalized_name
        )
    )
    if existing is not None:
        raise ValueError("An email template with this name already exists.")
    _validate_content(subject_template, text_body_template, html_body_template)

    template = ReportEmailTemplateRecord(
        name=normalized_name,
        subject_template=subject_template.strip(),
        text_body_template=text_body_template.strip(),
        html_body_template=(html_body_template or "").strip() or None,
        is_active=is_active,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template(
    db: Session,
    template: ReportEmailTemplateRecord,
    *,
    name: str,
    subject_template: str,
    text_body_template: str,
    html_body_template: str | None,
    is_active: bool,
) -> ReportEmailTemplateRecord:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Template name is required.")
    duplicate = db.scalar(
        select(ReportEmailTemplateRecord).where(
            ReportEmailTemplateRecord.name == normalized_name,
            ReportEmailTemplateRecord.id != template.id,
        )
    )
    if duplicate is not None:
        raise ValueError("An email template with this name already exists.")
    _validate_content(subject_template, text_body_template, html_body_template)

    template.name = normalized_name
    template.subject_template = subject_template.strip()
    template.text_body_template = text_body_template.strip()
    template.html_body_template = (html_body_template or "").strip() or None
    template.is_active = is_active
    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template: ReportEmailTemplateRecord) -> None:
    in_use = db.scalar(
        select(ScheduledReportConfigRecord.id).where(
            ScheduledReportConfigRecord.email_template_id == template.id
        )
    )
    if in_use is not None:
        raise ValueError(
            "This template is selected by a scheduled report. Select another template first."
        )
    db.delete(template)
    db.commit()


def render_template(content: str | None, variables: dict[str, object]) -> str | None:
    if content is None:
        return None

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(variables.get(key, ""))

    return _VARIABLE_PATTERN.sub(replace, content)


def report_variables(
    *,
    snapshot: dict,
    generated_at: datetime,
    unresolved_rows: int,
    recipient_count: int,
    test_mode: bool,
) -> dict[str, object]:
    return {
        "report_name": "Executive Duplicate Risk Report",
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "duplicate_groups": snapshot.get("duplicateGroups", 0),
        "duplicate_candidates": snapshot.get("duplicateCandidates", 0),
        "pending_review": snapshot.get("pendingReview", 0),
        "confirmed_duplicates": snapshot.get("confirmedDuplicates", 0),
        "awaiting_remediation": snapshot.get("awaitingRemediation", 0),
        "high_confidence_unresolved": snapshot.get("highConfidenceUnresolved", 0),
        "unresolved_rows": unresolved_rows,
        "recipient_count": recipient_count,
        "test_prefix": "TEST - " if test_mode else "",
    }
