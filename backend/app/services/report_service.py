from __future__ import annotations

import csv
import io
from datetime import datetime, time
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db_models.account import AccountRecord
from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.db_models.remediation_item import RemediationItemRecord
from app.db_models.review_decision_history import ReviewDecisionHistoryRecord
from app.db_models.scan import ScanRecord


REPORT_CATALOG: list[dict[str, Any]] = [
    {
        "type": "accounts",
        "name": "Account Inventory",
        "description": "Accounts collected from connected applications and scans.",
        "filters": ["integrationId", "application", "status", "search", "dateFrom", "dateTo"],
    },
    {
        "type": "duplicate_candidates",
        "name": "Duplicate Candidates",
        "description": "Duplicate candidate accounts with confidence and review outcome.",
        "filters": [
            "integrationId",
            "application",
            "decision",
            "minimumConfidence",
            "search",
            "dateFrom",
            "dateTo",
        ],
    },
    {
        "type": "review_decisions",
        "name": "Review Decisions",
        "description": "Reviewer decisions captured for duplicate account pairs.",
        "filters": [
            "integrationId",
            "application",
            "decision",
            "minimumConfidence",
            "reviewer",
            "dateFrom",
            "dateTo",
        ],
    },
    {
        "type": "remediation",
        "name": "Remediation",
        "description": "Duplicate-account remediation queue and action history.",
        "filters": [
            "integrationId",
            "application",
            "status",
            "minimumConfidence",
            "reviewer",
            "dateFrom",
            "dateTo",
        ],
    },
    {
        "type": "executions",
        "name": "Integration Executions",
        "description": "Integration execution history and processing statistics.",
        "filters": ["integrationId", "status", "dateFrom", "dateTo"],
    },
]


def get_report_catalog(db: Session) -> dict[str, Any]:
    integrations = db.scalars(
        select(IntegrationRecord).order_by(IntegrationRecord.name.asc())
    ).all()

    applications = sorted(
        {
            str(value)
            for value in db.scalars(
                select(AccountRecord.application).distinct()
            ).all()
            if value
        }
    )

    return {
        "reports": REPORT_CATALOG,
        "integrations": [
            {"id": item.id, "name": item.name}
            for item in integrations
        ],
        "applications": applications,
    }


def _date_bounds(
    date_from: str | None,
    date_to: str | None,
) -> tuple[datetime | None, datetime | None]:
    start = None
    end = None

    if date_from:
        start = datetime.combine(
            datetime.fromisoformat(date_from).date(),
            time.min,
        )
    if date_to:
        end = datetime.combine(
            datetime.fromisoformat(date_to).date(),
            time.max,
        )
    return start, end


def _contains(value: str) -> str:
    return f"%{value.strip()}%"


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _account_rows(db: Session, filters: dict[str, Any]):
    statement = (
        select(AccountRecord, ScanRecord, IntegrationRecord)
        .join(ScanRecord, ScanRecord.id == AccountRecord.scan_id)
        .outerjoin(IntegrationRecord, IntegrationRecord.id == ScanRecord.integration_id)
    )

    conditions = []
    if filters.get("integrationId"):
        conditions.append(ScanRecord.integration_id == filters["integrationId"])
    if filters.get("application"):
        conditions.append(AccountRecord.application == filters["application"])
    if filters.get("status"):
        conditions.append(AccountRecord.status == filters["status"])
    if filters.get("search"):
        term = _contains(filters["search"])
        conditions.append(
            or_(
                AccountRecord.username.ilike(term),
                AccountRecord.display_name.ilike(term),
                AccountRecord.email.ilike(term),
                AccountRecord.employee_id.ilike(term),
            )
        )

    start, end = _date_bounds(filters.get("dateFrom"), filters.get("dateTo"))
    if start:
        conditions.append(ScanRecord.created_at >= start)
    if end:
        conditions.append(ScanRecord.created_at <= end)
    if conditions:
        statement = statement.where(and_(*conditions))

    statement = statement.order_by(ScanRecord.created_at.desc(), AccountRecord.id.desc())

    return [
        {
            "accountId": account.id,
            "integration": integration.name if integration else None,
            "application": account.application,
            "username": account.username,
            "displayName": account.display_name,
            "email": account.email,
            "employeeId": account.employee_id,
            "department": account.department,
            "manager": account.manager,
            "status": account.status,
            "scanId": scan.id,
            "scanDate": _iso(scan.created_at),
        }
        for account, scan, integration in db.execute(statement).all()
    ]


def _candidate_rows(db: Session, filters: dict[str, Any]):
    statement = (
        select(
            DuplicateCandidateRecord,
            DuplicateGroupRecord,
            ScanRecord,
            IntegrationRecord,
        )
        .join(DuplicateGroupRecord, DuplicateGroupRecord.id == DuplicateCandidateRecord.group_id)
        .join(ScanRecord, ScanRecord.id == DuplicateGroupRecord.scan_id)
        .outerjoin(IntegrationRecord, IntegrationRecord.id == ScanRecord.integration_id)
    )

    conditions = []
    if filters.get("integrationId"):
        conditions.append(ScanRecord.integration_id == filters["integrationId"])
    if filters.get("application"):
        conditions.append(DuplicateGroupRecord.application == filters["application"])
    if filters.get("decision"):
        decision = filters["decision"]
        if decision == "PENDING":
            conditions.append(DuplicateCandidateRecord.review_decision.is_(None))
        else:
            conditions.append(DuplicateCandidateRecord.review_decision == decision)
    if filters.get("minimumConfidence") is not None:
        conditions.append(
            DuplicateCandidateRecord.confidence >= float(filters["minimumConfidence"])
        )
    if filters.get("search"):
        term = _contains(filters["search"])
        conditions.append(
            or_(
                DuplicateCandidateRecord.username.ilike(term),
                DuplicateGroupRecord.primary_username.ilike(term),
            )
        )

    start, end = _date_bounds(filters.get("dateFrom"), filters.get("dateTo"))
    if start:
        conditions.append(ScanRecord.created_at >= start)
    if end:
        conditions.append(ScanRecord.created_at <= end)
    if conditions:
        statement = statement.where(and_(*conditions))

    statement = statement.order_by(
        DuplicateCandidateRecord.confidence.desc(),
        DuplicateCandidateRecord.id.desc(),
    )

    return [
        {
            "candidateId": candidate.id,
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
            "reviewedAt": _iso(candidate.reviewed_at),
            "scanId": scan.id,
            "scanDate": _iso(scan.created_at),
        }
        for candidate, group, scan, integration in db.execute(statement).all()
    ]


def _review_rows(db: Session, filters: dict[str, Any]):
    statement = (
        select(ReviewDecisionHistoryRecord, IntegrationRecord)
        .outerjoin(
            IntegrationRecord,
            IntegrationRecord.id == ReviewDecisionHistoryRecord.integration_id,
        )
    )
    conditions = []
    if filters.get("integrationId"):
        conditions.append(
            ReviewDecisionHistoryRecord.integration_id == filters["integrationId"]
        )
    if filters.get("application"):
        conditions.append(ReviewDecisionHistoryRecord.application == filters["application"])
    if filters.get("decision"):
        conditions.append(ReviewDecisionHistoryRecord.decision == filters["decision"])
    if filters.get("minimumConfidence") is not None:
        conditions.append(
            ReviewDecisionHistoryRecord.confidence >= float(filters["minimumConfidence"])
        )
    if filters.get("reviewer"):
        conditions.append(
            ReviewDecisionHistoryRecord.reviewer_name.ilike(_contains(filters["reviewer"]))
        )
    start, end = _date_bounds(filters.get("dateFrom"), filters.get("dateTo"))
    if start:
        conditions.append(ReviewDecisionHistoryRecord.created_at >= start)
    if end:
        conditions.append(ReviewDecisionHistoryRecord.created_at <= end)
    if conditions:
        statement = statement.where(and_(*conditions))

    statement = statement.order_by(ReviewDecisionHistoryRecord.created_at.desc())
    return [
        {
            "decisionId": item.id,
            "integration": integration.name if integration else None,
            "application": item.application,
            "account1": item.account_1_key,
            "account2": item.account_2_key,
            "decision": item.decision,
            "confidence": item.confidence,
            "reviewer": item.reviewer_name,
            "comment": item.comment,
            "source": item.source,
            "createdAt": _iso(item.created_at),
        }
        for item, integration in db.execute(statement).all()
    ]


def _remediation_rows(db: Session, filters: dict[str, Any]):
    statement = (
        select(RemediationItemRecord, IntegrationRecord)
        .outerjoin(
            IntegrationRecord,
            IntegrationRecord.id == RemediationItemRecord.integration_id,
        )
    )
    conditions = []
    if filters.get("integrationId"):
        conditions.append(RemediationItemRecord.integration_id == filters["integrationId"])
    if filters.get("application"):
        conditions.append(RemediationItemRecord.application == filters["application"])
    if filters.get("status"):
        conditions.append(RemediationItemRecord.status == filters["status"])
    if filters.get("minimumConfidence") is not None:
        conditions.append(
            RemediationItemRecord.confidence >= float(filters["minimumConfidence"])
        )
    if filters.get("reviewer"):
        term = _contains(filters["reviewer"])
        conditions.append(
            or_(
                RemediationItemRecord.reviewer_name.ilike(term),
                RemediationItemRecord.actioned_by.ilike(term),
            )
        )
    start, end = _date_bounds(filters.get("dateFrom"), filters.get("dateTo"))
    if start:
        conditions.append(RemediationItemRecord.created_at >= start)
    if end:
        conditions.append(RemediationItemRecord.created_at <= end)
    if conditions:
        statement = statement.where(and_(*conditions))

    statement = statement.order_by(RemediationItemRecord.updated_at.desc())
    return [
        {
            "remediationId": item.id,
            "integration": integration.name if integration else None,
            "application": item.application,
            "account1": item.account_1_key,
            "account2": item.account_2_key,
            "confidence": item.confidence,
            "reviewer": item.reviewer_name,
            "status": item.status,
            "actionedBy": item.actioned_by,
            "reviewComment": item.review_comment,
            "actionComment": item.action_comment,
            "createdAt": _iso(item.created_at),
            "updatedAt": _iso(item.updated_at),
        }
        for item, integration in db.execute(statement).all()
    ]


def _execution_rows(db: Session, filters: dict[str, Any]):
    statement = (
        select(JobExecutionRecord, IntegrationRecord)
        .outerjoin(
            IntegrationRecord,
            IntegrationRecord.id == JobExecutionRecord.integration_id,
        )
    )
    conditions = []
    if filters.get("integrationId"):
        conditions.append(JobExecutionRecord.integration_id == filters["integrationId"])
    if filters.get("status"):
        conditions.append(JobExecutionRecord.status == filters["status"])
    start, end = _date_bounds(filters.get("dateFrom"), filters.get("dateTo"))
    if start:
        conditions.append(JobExecutionRecord.started_at >= start)
    if end:
        conditions.append(JobExecutionRecord.started_at <= end)
    if conditions:
        statement = statement.where(and_(*conditions))

    statement = statement.order_by(JobExecutionRecord.started_at.desc())
    return [
        {
            "executionId": item.id,
            "integration": integration.name if integration else None,
            "status": item.status,
            "scanId": item.scan_id,
            "sourceFileName": item.source_file_name,
            "accountsScanned": item.accounts_scanned,
            "duplicateGroups": item.duplicate_groups,
            "duplicateAccounts": item.duplicate_accounts,
            "errorMessage": item.error_message,
            "startedAt": _iso(item.started_at),
            "completedAt": _iso(item.completed_at),
        }
        for item, integration in db.execute(statement).all()
    ]


ROW_BUILDERS = {
    "accounts": _account_rows,
    "duplicate_candidates": _candidate_rows,
    "review_decisions": _review_rows,
    "remediation": _remediation_rows,
    "executions": _execution_rows,
}


def build_report(
    db: Session,
    report_type: str,
    filters: dict[str, Any],
    limit: int | None = None,
) -> dict[str, Any]:
    builder = ROW_BUILDERS.get(report_type)
    if builder is None:
        raise ValueError(f"Unsupported report type: {report_type}")

    rows = builder(db, filters)
    total = len(rows)
    if limit is not None:
        rows = rows[:limit]

    columns = list(rows[0].keys()) if rows else []
    return {
        "reportType": report_type,
        "total": total,
        "columns": columns,
        "rows": rows,
    }


def report_to_csv(report: dict[str, Any]) -> str:
    output = io.StringIO()
    columns = report.get("columns") or []
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    if columns:
        writer.writeheader()
        for row in report.get("rows", []):
            writer.writerow(row)
    return output.getvalue()
