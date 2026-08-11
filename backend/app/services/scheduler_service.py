from datetime import datetime
from threading import Lock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database.session import SessionLocal
from app.db_models.job_schedule import JobScheduleRecord
from app.services.scheduled_job_runner import (
    run_scheduled_integration,
)


class SchedulerService:
    """
    Manages the single APScheduler instance used by the application.
    """

    JOB_PREFIX = "integration_schedule_"

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )

        self._lock = Lock()

    @property
    def scheduler(self) -> BackgroundScheduler:
        return self._scheduler

    @property
    def running(self) -> bool:
        return self._scheduler.running

    @classmethod
    def build_job_id(
        cls,
        schedule_id: int,
    ) -> str:
        return f"{cls.JOB_PREFIX}{schedule_id}"

    @staticmethod
    def validate_timezone(
        timezone_name: str,
    ) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                f"Invalid timezone: {timezone_name}"
            ) from exc

    @classmethod
    def build_trigger(
        cls,
        schedule: JobScheduleRecord,
    ) -> CronTrigger:
        timezone = cls.validate_timezone(
            schedule.timezone
        )

        try:
            return CronTrigger.from_crontab(
                schedule.cron_expression,
                timezone=timezone,
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid cron expression "
                f"'{schedule.cron_expression}'. "
                "Expected five fields: "
                "minute hour day month day-of-week."
            ) from exc

    def start(self) -> None:
        with self._lock:
            if self._scheduler.running:
                return

            self._scheduler.start()

        self.reload_enabled_schedules()

        print("APScheduler started successfully.")

    def shutdown(
        self,
        *,
        wait: bool = False,
    ) -> None:
        with self._lock:
            if not self._scheduler.running:
                return

            self._scheduler.shutdown(
                wait=wait
            )

        print("APScheduler stopped successfully.")

    def register_schedule(
        self,
        schedule: JobScheduleRecord,
    ) -> Job | None:
        if not schedule.enabled:
            self.remove_schedule(
                schedule.id
            )
            return None

        trigger = self.build_trigger(
            schedule
        )

        job_id = self.build_job_id(
            schedule.id
        )

        job = self._scheduler.add_job(
            func=run_scheduled_integration,
            trigger=trigger,
            id=job_id,
            name=schedule.name,
            kwargs={
                "integration_id": (
                    schedule.integration_id
                ),
                "schedule_id": schedule.id,
            },
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=300,
        )

        self._update_next_run_time(
            schedule_id=schedule.id,
            next_run_time=job.next_run_time,
        )

        return job

    def remove_schedule(
        self,
        schedule_id: int,
    ) -> None:
        job_id = self.build_job_id(
            schedule_id
        )

        job = self._scheduler.get_job(
            job_id
        )

        if job is not None:
            self._scheduler.remove_job(
                job_id
            )

        self._update_next_run_time(
            schedule_id=schedule_id,
            next_run_time=None,
        )

    def pause_schedule(
        self,
        schedule_id: int,
    ) -> None:
        job_id = self.build_job_id(
            schedule_id
        )

        job = self._scheduler.get_job(
            job_id
        )

        if job is not None:
            self._scheduler.pause_job(
                job_id
            )

        self._update_next_run_time(
            schedule_id=schedule_id,
            next_run_time=None,
        )

    def resume_schedule(
        self,
        schedule_id: int,
    ) -> Job | None:
        db = SessionLocal()

        try:
            schedule = db.get(
                JobScheduleRecord,
                schedule_id,
            )

            if schedule is None:
                return None

            return self.register_schedule(
                schedule
            )

        finally:
            db.close()

    def reload_enabled_schedules(
        self,
    ) -> None:
        """
        Reload enabled schedules from the application's database.

        Existing integration jobs are removed first so reloads do not
        create duplicates.
        """

        self.remove_all_integration_jobs()

        db = SessionLocal()

        try:
            statement = (
                select(JobScheduleRecord)
                .where(
                    JobScheduleRecord.enabled.is_(
                        True
                    )
                )
                .order_by(
                    JobScheduleRecord.id.asc()
                )
            )

            schedules = list(
                db.scalars(statement).all()
            )

            loaded_count = 0

            for schedule in schedules:
                try:
                    self.register_schedule(
                        schedule
                    )

                    loaded_count += 1

                except Exception as exc:
                    schedule.last_run_status = (
                        "CONFIGURATION_ERROR"
                    )
                    schedule.last_error = str(exc)
                    schedule.next_run_at = None

                    db.commit()

                    print(
                        f"Unable to register schedule "
                        f"{schedule.id}: {exc}"
                    )

            print(
                f"Loaded {loaded_count} enabled "
                "integration schedule(s)."
            )

        finally:
            db.close()

    def remove_all_integration_jobs(
        self,
    ) -> None:
        for job in self._scheduler.get_jobs():
            if job.id.startswith(
                self.JOB_PREFIX
            ):
                self._scheduler.remove_job(
                    job.id
                )

    def get_job(
        self,
        schedule_id: int,
    ) -> Job | None:
        return self._scheduler.get_job(
            self.build_job_id(
                schedule_id
            )
        )

    def get_jobs(self) -> list[Job]:
        return [
            job
            for job in self._scheduler.get_jobs()
            if job.id.startswith(
                self.JOB_PREFIX
            )
        ]

    @staticmethod
    def _to_naive_utc(
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            return value

        return value.astimezone(
            ZoneInfo("UTC")
        ).replace(
            tzinfo=None
        )

    def _update_next_run_time(
        self,
        *,
        schedule_id: int,
        next_run_time: datetime | None,
    ) -> None:
        db = SessionLocal()

        try:
            schedule = db.get(
                JobScheduleRecord,
                schedule_id,
            )

            if schedule is None:
                return

            schedule.next_run_at = (
                self._to_naive_utc(
                    next_run_time
                )
            )

            db.commit()

        finally:
            db.close()


scheduler_service = SchedulerService()