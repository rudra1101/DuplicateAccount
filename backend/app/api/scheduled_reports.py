from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.scheduled_report import ScheduledReportRunRecord
from app.services.scheduled_report_scheduler import register_scheduled_report
from app.services.scheduled_report_service import (
    executive_duplicate_snapshot,
    get_or_create_scheduled_report_config,
    list_scheduled_report_runs,
    send_scheduled_duplicate_report,
    serialize_config,
    update_config,
)


router = APIRouter(
    prefix="/reports/schedule",
    tags=["Scheduled Reports"],
)


class ScheduledReportUpdate(BaseModel):
    enabled: bool = True
    frequency: str = Field(pattern="^(WEEKLY|MONTHLY|QUARTERLY)$")
    includeAdmins: bool = True
    recipientEmails: list[str] = []
    selectedColumns: list[str] = []


@router.get("", dependencies=[Depends(require_permission("report.manage_schedule"))])
def get_schedule(db: Session = Depends(get_db)):
    config = get_or_create_scheduled_report_config(db)
    return {
        "config": serialize_config(config),
        "snapshot": executive_duplicate_snapshot(db),
    }


@router.put("", dependencies=[Depends(require_permission("report.manage_schedule"))])
def update_schedule(
    payload: ScheduledReportUpdate,
    db: Session = Depends(get_db),
):
    try:
        config = update_config(
            db,
            enabled=payload.enabled,
            frequency=payload.frequency,
            include_admins=payload.includeAdmins,
            recipient_emails=payload.recipientEmails,
            selected_columns=payload.selectedColumns,
        )
        register_scheduled_report()
        db.refresh(config)
        return serialize_config(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/send-test", dependencies=[Depends(require_permission("report.manage_schedule"))])
def send_test_report(db: Session = Depends(get_db)):
    try:
        return send_scheduled_duplicate_report(db, test_mode=True)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to send scheduled report test email. The generated report remains available in report history.",
        ) from exc


@router.get("/history", dependencies=[Depends(require_permission("report.view"))])
def scheduled_report_history(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return {"runs": list_scheduled_report_runs(db, limit=limit)}


@router.get(
    "/history/{run_id}/download",
    dependencies=[Depends(require_permission("report.view"))],
)
def download_scheduled_report(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ScheduledReportRunRecord, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Scheduled report run not found.")

    return Response(
        content=run.csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{run.filename}"',
            "X-Report-Run-Id": str(run.id),
            "X-Report-Row-Count": str(run.row_count),
        },
    )
