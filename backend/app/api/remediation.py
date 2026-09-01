from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.services.remediation_service import (
    list_decision_history,
    list_remediation_items,
    update_remediation_status,
)
from app.services.service_desk_service import create_ticket, sync_ticket_by_id


router = APIRouter(prefix="/remediation", tags=["Remediation"])


class RemediationStatusRequest(BaseModel):
    status: str
    comment: str | None = None
    actionedBy: str | None = None


class CreateTicketRequest(BaseModel):
    target: str
    action: str
    requestedBy: str | None = None


@router.get("/")
def remediation_queue(
    status: str | None = Query(default="PENDING_ACTION"),
    integration_id: int | None = Query(default=None, alias="integrationId", ge=1),
    application: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.view")),
):
    try:
        items = list_remediation_items(
            db,
            status=status,
            integration_id=integration_id,
            application=application,
        )
        return {"count": len(items), "items": items}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Unable to load remediation queue.") from exc


@router.get("/history")
def decision_history(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.history.view")),
):
    try:
        items = list_decision_history(db, limit=limit)
        return {"count": len(items), "items": items}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Unable to load review decision history.") from exc


@router.post("/{item_id}/ticket")
def create_remediation_ticket(
    item_id: int,
    payload: CreateTicketRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    try:
        return create_ticket(
            db,
            item_id=item_id,
            target=payload.target,
            action=payload.action,
            requested_by=payload.requestedBy,
        )
    except ValueError as exc:
        message = str(exc)
        raise HTTPException(status_code=404 if "not found" in message.lower() else 400, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{item_id}/ticket/sync")
def sync_remediation_ticket(
    item_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    try:
        return sync_ticket_by_id(db, item_id)
    except ValueError as exc:
        message = str(exc)
        raise HTTPException(status_code=404 if "not found" in message.lower() else 400, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{item_id}/status")
def set_remediation_status(
    item_id: int,
    payload: RemediationStatusRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    try:
        return update_remediation_status(
            db,
            item_id=item_id,
            status=payload.status,
            action_comment=payload.comment,
            actioned_by=payload.actionedBy,
        )
    except ValueError as exc:
        message = str(exc)
        raise HTTPException(
            status_code=404 if "not found" in message.lower() else 400,
            detail=message,
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Unable to update remediation item.") from exc
