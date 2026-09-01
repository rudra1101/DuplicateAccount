from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.services.report_service import (
    build_report,
    get_report_catalog,
    report_to_csv,
)


router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(require_permission("report.view"))],
)


class ReportFilters(BaseModel):
    integrationId: int | None = Field(default=None, gt=0)
    application: str | None = None
    status: str | None = None
    decision: str | None = None
    minimumConfidence: float | None = Field(default=None, ge=0, le=100)
    reviewer: str | None = None
    search: str | None = None
    dateFrom: str | None = None
    dateTo: str | None = None


class ReportRequest(BaseModel):
    reportType: str = Field(min_length=1, max_length=100)
    filters: ReportFilters = Field(default_factory=ReportFilters)


def _csv_response(report_type: str, report: dict) -> Response:
    csv_content = report_to_csv(report)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type}_{timestamp}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Total": str(report["total"]),
        },
    )


@router.get("/catalog")
def report_catalog(db: Session = Depends(get_db)):
    return get_report_catalog(db)


@router.get("/rudrix-download")
def rudrix_report_download(
    report_type: str = Query(alias="reportType", min_length=1, max_length=100),
    integration_id: int | None = Query(default=None, alias="integrationId", gt=0),
    application: str | None = Query(default=None),
    status: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    minimum_confidence: float | None = Query(
        default=None,
        alias="minimumConfidence",
        ge=0,
        le=100,
    ),
    reviewer: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    db: Session = Depends(get_db),
):
    filters = {
        "integrationId": integration_id,
        "application": application,
        "status": status,
        "decision": decision,
        "minimumConfidence": minimum_confidence,
        "reviewer": reviewer,
        "search": search,
        "dateFrom": date_from,
        "dateTo": date_to,
    }
    filters = {
        key: value
        for key, value in filters.items()
        if value not in (None, "")
    }

    try:
        report = build_report(
            db,
            report_type,
            filters,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _csv_response(report_type, report)


@router.post("/preview")
def report_preview(
    payload: ReportRequest,
    db: Session = Depends(get_db),
):
    try:
        return build_report(
            db,
            payload.reportType,
            payload.filters.model_dump(exclude_none=True),
            limit=100,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/download")
def report_download(
    payload: ReportRequest,
    db: Session = Depends(get_db),
):
    try:
        report = build_report(
            db,
            payload.reportType,
            payload.filters.model_dump(exclude_none=True),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _csv_response(payload.reportType, report)
