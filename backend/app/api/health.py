from fastapi import APIRouter

from app.services.scheduler_service import (
    scheduler_service,
)


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/")
def health():
    jobs = scheduler_service.get_jobs()

    return {
        "status": "healthy",
        "scheduler": {
            "running": scheduler_service.running,
            "registeredJobs": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "nextRunTime": (
                        job.next_run_time.isoformat()
                        if job.next_run_time
                        else None
                    ),
                }
                for job in jobs
            ],
        },
    }