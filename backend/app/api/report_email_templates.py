from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.report_email_template import ReportEmailTemplateRecord
from app.services.report_email_template_service import (
    VARIABLES,
    create_template,
    delete_template,
    list_templates,
    serialize_template,
    update_template,
)


router = APIRouter(prefix="/reports/email-templates", tags=["Report Email Templates"])


class EmailTemplatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    subjectTemplate: str = Field(min_length=1, max_length=300)
    textBodyTemplate: str = Field(min_length=1)
    htmlBodyTemplate: str = ""
    isActive: bool = True


@router.get("", dependencies=[Depends(require_permission("report.manage_templates"))])
def get_templates(db: Session = Depends(get_db)):
    return {
        "variables": VARIABLES,
        "templates": [serialize_template(item) for item in list_templates(db)],
    }


@router.post("", dependencies=[Depends(require_permission("report.manage_templates"))])
def post_template(payload: EmailTemplatePayload, db: Session = Depends(get_db)):
    try:
        template = create_template(
            db,
            name=payload.name,
            subject_template=payload.subjectTemplate,
            text_body_template=payload.textBodyTemplate,
            html_body_template=payload.htmlBodyTemplate,
            is_active=payload.isActive,
        )
        return serialize_template(template)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put(
    "/{template_id}",
    dependencies=[Depends(require_permission("report.manage_templates"))],
)
def put_template(
    template_id: int,
    payload: EmailTemplatePayload,
    db: Session = Depends(get_db),
):
    template = db.get(ReportEmailTemplateRecord, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Email template not found.")
    try:
        return serialize_template(
            update_template(
                db,
                template,
                name=payload.name,
                subject_template=payload.subjectTemplate,
                text_body_template=payload.textBodyTemplate,
                html_body_template=payload.htmlBodyTemplate,
                is_active=payload.isActive,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/{template_id}",
    dependencies=[Depends(require_permission("report.manage_templates"))],
)
def remove_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(ReportEmailTemplateRecord, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Email template not found.")
    try:
        delete_template(db, template)
        return {"deleted": True}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
