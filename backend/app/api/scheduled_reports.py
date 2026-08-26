from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.services.scheduled_report_scheduler import register_scheduled_report
from app.services.scheduled_report_service import (
    executive_duplicate_snapshot,
    get_or_create_scheduled_report_config,
    send_scheduled_duplicate_report,
    serialize_config,
    update_config,
)


router = APIRouter(
    prefix="/reports/schedule",
    tags=["Scheduled Reports"],
    dependencies=[Depends(require_permission("report.manage_schedule"))],
)


class ScheduledReportUpdate(BaseModel):
    enabled: bool = True
    frequency: str = Field(pattern="^(WEEKLY|MONTHLY|QUARTERLY)$")
    includeAdmins: bool = True
    recipientEmails: list[str] = []
    selectedColumns: list[str] = []


@router.get("")
def get_schedule(db: Session = Depends(get_db)):
    config = get_or_create_scheduled_report_config(db)
    return {
        "config": serialize_config(config),
        "snapshot": executive_duplicate_snapshot(db),
    }


@router.put("")
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


@router.post("/send-test")
def send_test_report(db: Session = Depends(get_db)):
    try:
        return send_scheduled_duplicate_report(db, test_mode=True)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to send scheduled report test email.",
        ) from exc
