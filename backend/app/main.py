from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai_health import router as ai_health_router
from app.api.application_schemas import router as application_schemas_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.chat_feedback import router as chat_feedback_router
from app.api.chat_history import router as chat_history_router
from app.api.chat_stream import router as chat_stream_router
from app.api.dashboard import router as dashboard_router
from app.api.detect import router as detect_router
from app.api.health import router as health_router
from app.api.integrations import router as integrations_router
from app.api.job_schedules import router as job_schedules_router
from app.api.knowledge import router as knowledge_router
from app.api.matching_policy import router as matching_policy_router
from app.api.ml_models import router as ml_router
from app.api.operations import router as operations_router
from app.api.reports import router as reports_router
from app.api.scheduled_reports import router as scheduled_reports_router
from app.api.review import router as review_router
from app.api.remediation import router as remediation_router
from app.api.roles import router as roles_router
from app.api.scans import router as scans_router
from app.api.upload import router as upload_router
from app.api.users import router as users_router
from app.api.vector_search import router as vector_search_router
from app.auth.middleware import authentication_middleware
from app.database.base import Base
from app.database.session import IS_SQLITE, SessionLocal, engine
from app.observability import (
    configure_logging,
    metrics_response,
    observability_middleware,
    unhandled_exception_handler,
)
from app.services.rbac_service import seed_rbac
from app.services.scheduler_service import scheduler_service
from app.services.scheduled_report_scheduler import register_scheduled_report

import app.connectors  # noqa: F401
import app.db_models  # noqa: F401


configure_logging()

# SQLite remains a lightweight backwards-compatible fallback for local/test use.
# PostgreSQL schema changes are owned by Alembic and must be applied with
# `alembic upgrade head` before application startup.
if IS_SQLITE:
    Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    seed_rbac(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service.start()
    register_scheduled_report()
    try:
        yield
    finally:
        scheduler_service.shutdown(wait=False)


app = FastAPI(
    title="Duplicate Account Detection API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, unhandled_exception_handler)
app.middleware("http")(authentication_middleware)
app.middleware("http")(observability_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_response()


app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(ai_health_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(detect_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(remediation_router, prefix="/api")
app.include_router(scans_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(application_schemas_router, prefix="/api")
app.include_router(matching_policy_router, prefix="/api")
app.include_router(job_schedules_router, prefix="/api")
app.include_router(operations_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(scheduled_reports_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(ml_router, prefix="/api")
app.include_router(vector_search_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(chat_history_router, prefix="/api")
app.include_router(chat_feedback_router, prefix="/api")
app.include_router(chat_stream_router, prefix="/api")
