from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger

from app.database.session import SessionLocal
from app.services.scheduled_report_service import (
    get_or_create_scheduled_report_config,
    send_scheduled_duplicate_report,
)
from app.services.scheduler_service import scheduler_service


REPORT_JOB_ID = "scheduled_duplicate_risk_report"


def _trigger_for(frequency: str, timezone_name: str) -> CronTrigger:
    timezone = ZoneInfo(timezone_name)
    normalized = frequency.upper()

    if normalized == "WEEKLY":
        return CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=timezone)
    if normalized == "MONTHLY":
        return CronTrigger(day=1, hour=9, minute=0, timezone=timezone)
    if normalized == "QUARTERLY":
        return CronTrigger(month="1,4,7,10", day=1, hour=9, minute=0, timezone=timezone)

    raise ValueError("Unsupported scheduled report frequency.")


def _to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def run_scheduled_duplicate_report() -> None:
    db = SessionLocal()
    try:
        send_scheduled_duplicate_report(db)
    finally:
        db.close()


def register_scheduled_report() -> None:
    db = SessionLocal()
    try:
        config = get_or_create_scheduled_report_config(db)

        existing = scheduler_service.scheduler.get_job(REPORT_JOB_ID)
        if existing is not None:
            scheduler_service.scheduler.remove_job(REPORT_JOB_ID)

        if not config.enabled:
            config.next_run_at = None
            db.commit()
            return

        job = scheduler_service.scheduler.add_job(
            func=run_scheduled_duplicate_report,
            trigger=_trigger_for(config.frequency, config.timezone),
            id=REPORT_JOB_ID,
            name="IdentityAI Duplicate Risk Report",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
        config.next_run_at = _to_naive_utc(job.next_run_time)
        db.commit()
    finally:
        db.close()
