from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database.session import DATABASE_BACKEND, engine
from app.db_models.account import AccountRecord
from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.db_models.remediation_item import RemediationItemRecord
from app.db_models.scan import ScanRecord
from app.services.scheduler_service import scheduler_service


def _pool_value(name: str) -> int | None:
    attribute = getattr(engine.pool, name, None)
    if attribute is None:
        return None

    try:
        value = attribute() if callable(attribute) else attribute
        return int(value)
    except (TypeError, ValueError):
        return None


def _execution_counts(db: Session) -> dict[str, int]:
    row = db.execute(
        select(
            func.count(JobExecutionRecord.id).label("total"),
            func.coalesce(
                func.sum(case((JobExecutionRecord.status == "RUNNING", 1), else_=0)),
                0,
            ).label("running"),
            func.coalesce(
                func.sum(case((JobExecutionRecord.status == "COMPLETED", 1), else_=0)),
                0,
            ).label("completed"),
            func.coalesce(
                func.sum(case((JobExecutionRecord.status == "FAILED", 1), else_=0)),
                0,
            ).label("failed"),
        )
    ).one()

    return {
        "total": int(row.total or 0),
        "running": int(row.running or 0),
        "completed": int(row.completed or 0),
        "failed": int(row.failed or 0),
    }


def _integration_counts(db: Session) -> dict[str, int]:
    row = db.execute(
        select(
            func.count(IntegrationRecord.id).label("total"),
            func.coalesce(
                func.sum(case((IntegrationRecord.enabled.is_(True), 1), else_=0)),
                0,
            ).label("enabled"),
            func.coalesce(
                func.sum(case((IntegrationRecord.enabled.is_(False), 1), else_=0)),
                0,
            ).label("disabled"),
        )
    ).one()

    return {
        "total": int(row.total or 0),
        "enabled": int(row.enabled or 0),
        "disabled": int(row.disabled or 0),
    }


def get_system_status(db: Session) -> dict[str, Any]:
    # The first lightweight query doubles as the database connectivity check.
    db.execute(select(1)).scalar_one()

    jobs = scheduler_service.get_jobs()
    scheduler_running = bool(scheduler_service.running)

    executions = _execution_counts(db)
    integrations = _integration_counts(db)

    scans = int(db.scalar(select(func.count(ScanRecord.id))) or 0)
    accounts = int(db.scalar(select(func.count(AccountRecord.id))) or 0)
    duplicate_groups = int(db.scalar(select(func.count(DuplicateGroupRecord.id))) or 0)
    duplicate_candidates = int(db.scalar(select(func.count(DuplicateCandidateRecord.id))) or 0)
    pending_remediation = int(
        db.scalar(
            select(func.count(RemediationItemRecord.id)).where(
                RemediationItemRecord.status == "PENDING_ACTION"
            )
        )
        or 0
    )

    pool = {
        "size": _pool_value("size"),
        "checkedOut": _pool_value("checkedout"),
        "checkedIn": _pool_value("checkedin"),
        "overflow": _pool_value("overflow"),
    }

    overall_status = "healthy" if scheduler_running else "degraded"

    return {
        "status": overall_status,
        "generatedAt": datetime.now(UTC).isoformat(),
        "database": {
            "status": "healthy",
            "backend": DATABASE_BACKEND,
            "pool": pool,
        },
        "scheduler": {
            "status": "healthy" if scheduler_running else "degraded",
            "running": scheduler_running,
            "registeredJobs": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "nextRunTime": job.next_run_time.isoformat() if job.next_run_time else None,
                }
                for job in jobs
            ],
        },
        "application": {
            "integrations": integrations,
            "executions": executions,
            "scans": scans,
            "accounts": accounts,
            "duplicateGroups": duplicate_groups,
            "duplicateCandidates": duplicate_candidates,
            "pendingRemediation": pending_remediation,
        },
    }
