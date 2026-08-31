from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database.session import SessionLocal
from app.services.scheduler_service import scheduler_service


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/live")
def liveness():
    return {"status": "alive"}


@router.get("/ready")
def readiness():
    database_ok = False
    database_error = None

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        database_ok = True
    except Exception as exc:
        database_error = exc.__class__.__name__

    payload = {
        "status": "ready" if database_ok else "not_ready",
        "checks": {
            "database": {
                "status": "healthy" if database_ok else "unhealthy",
                "error": database_error,
            },
            "scheduler": {
                "status": "healthy" if scheduler_service.running else "degraded",
                "running": scheduler_service.running,
            },
        },
    }

    if not database_ok:
        return JSONResponse(status_code=503, content=payload)
    return payload


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
