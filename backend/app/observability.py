from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


REQUEST_COUNT = Counter(
    "identityai_http_requests_total",
    "Total HTTP requests handled by IdentityAI.",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "identityai_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)
IN_PROGRESS = Gauge(
    "identityai_http_requests_in_progress",
    "HTTP requests currently being processed.",
    ["method"],
)

DATABASE_POOL_SIZE = Gauge(
    "identityai_database_pool_size",
    "Configured SQLAlchemy connection pool size.",
)
DATABASE_POOL_CHECKED_OUT = Gauge(
    "identityai_database_pool_checked_out",
    "SQLAlchemy database connections currently checked out.",
)
DATABASE_POOL_OVERFLOW = Gauge(
    "identityai_database_pool_overflow",
    "Current SQLAlchemy connection pool overflow.",
)
SCHEDULER_RUNNING = Gauge(
    "identityai_scheduler_running",
    "Whether the IdentityAI scheduler is running (1=yes, 0=no).",
)
SCHEDULER_JOBS = Gauge(
    "identityai_scheduler_jobs",
    "Number of registered scheduler jobs.",
)
INTEGRATIONS = Gauge(
    "identityai_integrations",
    "Integration count by state.",
    ["state"],
)
EXECUTIONS = Gauge(
    "identityai_job_executions",
    "Job execution count by status.",
    ["status"],
)
SCANS = Gauge(
    "identityai_scans_total_current",
    "Current number of scan records.",
)
ACCOUNTS = Gauge(
    "identityai_accounts_total_current",
    "Current number of account records.",
)
DUPLICATE_GROUPS = Gauge(
    "identityai_duplicate_groups_total_current",
    "Current number of duplicate groups.",
)
DUPLICATE_CANDIDATES = Gauge(
    "identityai_duplicate_candidates_total_current",
    "Current number of duplicate candidates.",
)
PENDING_REMEDIATION = Gauge(
    "identityai_pending_remediation_total_current",
    "Current number of remediation items pending action.",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


logger = logging.getLogger("identityai.http")


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or request.url.path


async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    method = request.method
    started = time.perf_counter()
    client_ip = request.client.host if request.client else None
    IN_PROGRESS.labels(method=method).inc()

    response = None
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_seconds = time.perf_counter() - started
        path = _route_template(request)

        IN_PROGRESS.labels(method=method).dec()
        REQUEST_COUNT.labels(
            method=method,
            path=path,
            status=str(status_code),
        ).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(duration_seconds)

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_seconds * 1000, 2),
                "client_ip": client_ip,
            },
        )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    logger.exception(
        "unhandled_exception",
        exc_info=exc,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error.",
            "requestId": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


def update_operational_gauges(snapshot: dict) -> None:
    database = snapshot.get("database", {})
    pool = database.get("pool", {})

    if pool.get("size") is not None:
        DATABASE_POOL_SIZE.set(pool["size"])
    if pool.get("checkedOut") is not None:
        DATABASE_POOL_CHECKED_OUT.set(pool["checkedOut"])
    if pool.get("overflow") is not None:
        DATABASE_POOL_OVERFLOW.set(pool["overflow"])

    scheduler = snapshot.get("scheduler", {})
    SCHEDULER_RUNNING.set(1 if scheduler.get("running") else 0)
    SCHEDULER_JOBS.set(int(scheduler.get("registeredJobs", 0) or 0))

    application = snapshot.get("application", {})
    integrations = application.get("integrations", {})
    for state in ("total", "enabled", "disabled"):
        INTEGRATIONS.labels(state=state).set(int(integrations.get(state, 0) or 0))

    executions = application.get("executions", {})
    for status in ("total", "running", "completed", "failed"):
        EXECUTIONS.labels(status=status).set(int(executions.get(status, 0) or 0))

    SCANS.set(int(application.get("scans", 0) or 0))
    ACCOUNTS.set(int(application.get("accounts", 0) or 0))
    DUPLICATE_GROUPS.set(int(application.get("duplicateGroups", 0) or 0))
    DUPLICATE_CANDIDATES.set(int(application.get("duplicateCandidates", 0) or 0))
    PENDING_REMEDIATION.set(int(application.get("pendingRemediation", 0) or 0))


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
