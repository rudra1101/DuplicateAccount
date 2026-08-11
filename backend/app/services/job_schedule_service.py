from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.integration import IntegrationRecord
from app.db_models.job_schedule import JobScheduleRecord
from app.schemas.job_schedule import (
    JobScheduleCreate,
    JobScheduleUpdate,
)
from app.services.scheduler_service import scheduler_service


def convert_utc_to_timezone(
    value: datetime | None,
    timezone_name: str,
) -> str | None:
    """
    Convert a UTC database timestamp into the schedule's selected timezone.

    Current database values are stored as naive UTC datetimes.
    If a timezone-aware datetime is received, it is normalized to UTC first.
    """

    if value is None:
        return None

    try:
        target_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        target_timezone = ZoneInfo("UTC")

    if value.tzinfo is None:
        utc_value = value.replace(tzinfo=UTC)
    else:
        utc_value = value.astimezone(UTC)

    return utc_value.astimezone(
        target_timezone
    ).isoformat()


def schedule_to_dict(
    schedule: JobScheduleRecord,
) -> dict[str, Any]:
    timezone_name = (
        schedule.timezone
        or "UTC"
    )

    return {
        "id": schedule.id,
        "integrationId": schedule.integration_id,
        "name": schedule.name,
        "scheduleType": schedule.schedule_type,
        "cronExpression": schedule.cron_expression,
        "timezone": timezone_name,
        "enabled": schedule.enabled,
        "lastRunAt": convert_utc_to_timezone(
            schedule.last_run_at,
            timezone_name,
        ),
        "lastRunStatus": schedule.last_run_status,
        "nextRunAt": convert_utc_to_timezone(
            schedule.next_run_at,
            timezone_name,
        ),
        "lastError": schedule.last_error,
        "createdAt": convert_utc_to_timezone(
            schedule.created_at,
            timezone_name,
        ),
        "updatedAt": convert_utc_to_timezone(
            schedule.updated_at,
            timezone_name,
        ),
    }


def get_schedule_by_integration(
    db: Session,
    integration_id: int,
) -> JobScheduleRecord | None:
    statement = (
        select(JobScheduleRecord)
        .where(
            JobScheduleRecord.integration_id
            == integration_id
        )
        .limit(1)
    )

    return db.scalars(
        statement
    ).first()


def refresh_schedule(
    db: Session,
    schedule_id: int,
) -> JobScheduleRecord:
    """
    Reload the schedule after SchedulerService updates next_run_at
    through a separate SQLAlchemy session.
    """

    db.expire_all()

    refreshed_schedule = db.get(
        JobScheduleRecord,
        schedule_id,
    )

    if refreshed_schedule is None:
        raise ValueError(
            "Schedule no longer exists."
        )

    return refreshed_schedule


def create_schedule(
    db: Session,
    *,
    integration: IntegrationRecord,
    payload: JobScheduleCreate,
) -> JobScheduleRecord:
    existing = get_schedule_by_integration(
        db=db,
        integration_id=integration.id,
    )

    if existing is not None:
        raise ValueError(
            "A schedule already exists for this integration."
        )

    schedule = JobScheduleRecord(
        integration_id=integration.id,
        name=payload.name.strip(),
        schedule_type="CRON",
        cron_expression=payload.cronExpression.strip(),
        timezone=payload.timezone.strip(),
        enabled=payload.enabled,
    )

    scheduler_service.build_trigger(
        schedule
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    schedule_id = schedule.id

    if schedule.enabled:
        scheduler_service.register_schedule(
            schedule
        )
    else:
        scheduler_service.remove_schedule(
            schedule_id
        )

    return refresh_schedule(
        db=db,
        schedule_id=schedule_id,
    )


def update_schedule(
    db: Session,
    *,
    schedule: JobScheduleRecord,
    payload: JobScheduleUpdate,
) -> JobScheduleRecord:
    update_data = payload.model_dump(
        exclude_unset=True
    )

    if "name" in update_data:
        schedule.name = (
            update_data["name"].strip()
        )

    if "cronExpression" in update_data:
        schedule.cron_expression = (
            update_data[
                "cronExpression"
            ].strip()
        )

    if "timezone" in update_data:
        schedule.timezone = (
            update_data[
                "timezone"
            ].strip()
        )

    if "enabled" in update_data:
        schedule.enabled = (
            update_data["enabled"]
        )

    scheduler_service.build_trigger(
        schedule
    )

    schedule_id = schedule.id

    db.commit()
    db.refresh(schedule)

    if schedule.enabled:
        scheduler_service.register_schedule(
            schedule
        )
    else:
        scheduler_service.remove_schedule(
            schedule_id
        )

    return refresh_schedule(
        db=db,
        schedule_id=schedule_id,
    )


def delete_schedule(
    db: Session,
    *,
    schedule: JobScheduleRecord,
) -> None:
    schedule_id = schedule.id

    scheduler_service.remove_schedule(
        schedule_id
    )

    db.delete(schedule)
    db.commit()


def enable_schedule(
    db: Session,
    *,
    schedule: JobScheduleRecord,
) -> JobScheduleRecord:
    schedule.enabled = True

    scheduler_service.build_trigger(
        schedule
    )

    schedule_id = schedule.id

    db.commit()
    db.refresh(schedule)

    scheduler_service.register_schedule(
        schedule
    )

    return refresh_schedule(
        db=db,
        schedule_id=schedule_id,
    )


def disable_schedule(
    db: Session,
    *,
    schedule: JobScheduleRecord,
) -> JobScheduleRecord:
    schedule.enabled = False

    schedule_id = schedule.id

    db.commit()
    db.refresh(schedule)

    scheduler_service.remove_schedule(
        schedule_id
    )

    return refresh_schedule(
        db=db,
        schedule_id=schedule_id,
    )