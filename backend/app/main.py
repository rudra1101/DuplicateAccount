from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

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
from app.api.report_email_templates import router as report_email_templates_router
from app.api.reports import router as reports_router
from app.api.scheduled_reports import router as scheduled_reports_router
from app.api.review import router as review_router
from app.api.remediation import router as remediation_router
from app.api.roles import router as roles_router
from app.api.scans import router as scans_router
from app.api.settings import router as settings_router
from app.api.upload import router as upload_router
from app.api.users import router as users_router
from app.api.vector_search import router as vector_search_router
from app.auth.middleware import authentication_middleware
from app.config import get_runtime_settings, validate_runtime_configuration
from app.database.base import Base
from app.database.session import IS_SQLITE, SessionLocal, engine
from app.observability import (
    configure_logging,
    logger,
    metrics_response,
    observability_middleware,
    unhandled_exception_handler,
    update_operational_gauges,
)
from app.security_headers import security_headers_middleware
from app.services.monitoring_service import get_system_status
from app.services.rbac_service import seed_rbac
from app.services.remediation_sla_service import process_remediation_sla
from app.services.scheduler_service import scheduler_service
from app.services.scheduled_report_scheduler import register_scheduled_report
from app.services.service_desk_service import sync_open_tickets

import app.connectors  # noqa: F401
import app.db_models  # noqa: F401


configure_logging()
settings = get_runtime_settings()
validate_runtime_configuration(settings)

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
    scheduler_service.scheduler.add_job(
        sync_open_tickets,
        trigger="interval",
        minutes=5,
        id="service_desk_ticket_sync",
        name="Service Desk ticket status synchronization",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler_service.scheduler.add_job(
        process_remediation_sla,
        trigger="interval",
        minutes=15,
        id="remediation_sla_escalation",
        name="Remediation SLA escalation",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
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
if settings.security_headers_enabled:
    app.middleware("http")(security_headers_middleware)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=list(settings.allowed_hosts),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Content-Disposition", "X-Report-Total"],
)


@app.get("/metrics", include_in_schema=False)
def metrics():
    # Metrics must remain scrapeable even if a domain/database snapshot fails.
    try:
        with SessionLocal() as db:
            update_operational_gauges(get_system_status(db))
    except Exception:
        logger.exception("operational_metric_refresh_failed")

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
app.include_router(report_email_templates_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(ml_router, prefix="/api")
app.include_router(vector_search_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(chat_history_router, prefix="/api")
app.include_router(chat_feedback_router, prefix="/api")
app.include_router(chat_stream_router, prefix="/api")
