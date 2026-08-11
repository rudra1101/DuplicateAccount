from datetime import datetime

from app.database.session import SessionLocal
from app.db_models.integration import IntegrationRecord
from app.db_models.job_schedule import JobScheduleRecord
from app.services.integration_ingestion_service import (
    execute_integration,
)


def run_scheduled_integration(
    integration_id: int,
    schedule_id: int,
) -> None:
    """
    Entry point called by APScheduler.

    A fresh SQLAlchemy session is created because scheduled jobs run
    outside the lifetime of a FastAPI request.
    """

    db = SessionLocal()

    try:
        schedule = db.get(
            JobScheduleRecord,
            schedule_id,
        )

        integration = db.get(
            IntegrationRecord,
            integration_id,
        )

        if schedule is None:
            print(
                f"Scheduled job skipped: schedule {schedule_id} "
                "was not found."
            )
            return

        if integration is None:
            schedule.last_run_at = datetime.utcnow()
            schedule.last_run_status = "FAILED"
            schedule.last_error = (
                f"Integration {integration_id} was not found."
            )

            db.commit()
            return

        if not schedule.enabled:
            print(
                f"Scheduled job skipped: schedule {schedule_id} "
                "is disabled."
            )
            return

        if not integration.enabled:
            schedule.last_run_at = datetime.utcnow()
            schedule.last_run_status = "SKIPPED"
            schedule.last_error = (
                "The integration is disabled."
            )

            db.commit()
            return

        schedule.last_run_at = datetime.utcnow()
        schedule.last_run_status = "RUNNING"
        schedule.last_error = None

        db.commit()

        execute_integration(
            db=db,
            integration=integration,
        )

        schedule = db.get(
            JobScheduleRecord,
            schedule_id,
        )

        if schedule is not None:
            schedule.last_run_at = datetime.utcnow()
            schedule.last_run_status = "COMPLETED"
            schedule.last_error = None

            db.commit()

        print(
            f"Scheduled integration completed: "
            f"integration={integration_id}, "
            f"schedule={schedule_id}"
        )

    except Exception as exc:
        db.rollback()

        schedule = db.get(
            JobScheduleRecord,
            schedule_id,
        )

        if schedule is not None:
            schedule.last_run_at = datetime.utcnow()
            schedule.last_run_status = "FAILED"
            schedule.last_error = str(exc)

            db.commit()

        print(
            f"Scheduled integration failed: "
            f"integration={integration_id}, "
            f"schedule={schedule_id}, "
            f"error={exc}"
        )

    finally:
        db.close()