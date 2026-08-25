from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/catalog")
def report_catalog(db: Session = Depends(get_db)):
    return get_report_catalog(db)


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

    csv_content = report_to_csv(report)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{payload.reportType}_{timestamp}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Total": str(report["total"]),
        },
    )
