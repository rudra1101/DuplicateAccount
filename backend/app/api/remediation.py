from __future__ import annotations

from pydantic import BaseModel, Field
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


class BulkTicketRequest(CreateTicketRequest):
    itemIds: list[int] = Field(min_length=1, max_length=100)


class BulkItemsRequest(BaseModel):
    itemIds: list[int] = Field(min_length=1, max_length=100)
    actionedBy: str | None = None


def _bulk_result(item_id: int, callback):
    try:
        result = callback()
        return {"itemId": item_id, "success": True, "result": result, "error": None}
    except Exception as exc:
        return {"itemId": item_id, "success": False, "result": None, "error": str(exc)}


@router.get("/")
def remediation_queue(
    status: str | None = Query(default="PENDING_ACTION"),
    integration_id: int | None = Query(default=None, alias="integrationId", ge=1),
    application: str | None = Query(default=None),
    min_confidence: float | None = Query(default=None, alias="minConfidence", ge=0, le=100),
    max_confidence: float | None = Query(default=None, alias="maxConfidence", ge=0, le=100),
    remediation_action: str | None = Query(default=None, alias="remediationAction"),
    ticket_status: str | None = Query(default=None, alias="ticketStatus"),
    has_ticket: bool | None = Query(default=None, alias="hasTicket"),
    sla_status: str | None = Query(default=None, alias="slaStatus"),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.view")),
):
    try:
        items = list_remediation_items(
            db,
            status=status,
            integration_id=integration_id,
            application=application,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            remediation_action=remediation_action,
            ticket_status=ticket_status,
            has_ticket=has_ticket,
            sla_status=sla_status,
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


@router.post("/bulk/tickets")
def create_bulk_remediation_tickets(
    payload: BulkTicketRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    results = [
        _bulk_result(
            item_id,
            lambda item_id=item_id: create_ticket(
                db,
                item_id=item_id,
                target=payload.target,
                action=payload.action,
                requested_by=payload.requestedBy,
            ),
        )
        for item_id in dict.fromkeys(payload.itemIds)
    ]
    return {
        "requested": len(results),
        "succeeded": sum(1 for item in results if item["success"]),
        "failed": sum(1 for item in results if not item["success"]),
        "results": results,
    }


@router.post("/bulk/tickets/sync")
def sync_bulk_remediation_tickets(
    payload: BulkItemsRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    results = [
        _bulk_result(item_id, lambda item_id=item_id: sync_ticket_by_id(db, item_id))
        for item_id in dict.fromkeys(payload.itemIds)
    ]
    return {
        "requested": len(results),
        "succeeded": sum(1 for item in results if item["success"]),
        "failed": sum(1 for item in results if not item["success"]),
        "results": results,
    }


@router.post("/bulk/ignore")
def ignore_bulk_remediation_items(
    payload: BulkItemsRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    results = [
        _bulk_result(
            item_id,
            lambda item_id=item_id: update_remediation_status(
                db,
                item_id=item_id,
                status="IGNORED",
                action_comment="Ignored through bulk remediation action.",
                actioned_by=payload.actionedBy,
            ),
        )
        for item_id in dict.fromkeys(payload.itemIds)
    ]
    return {
        "requested": len(results),
        "succeeded": sum(1 for item in results if item["success"]),
        "failed": sum(1 for item in results if not item["success"]),
        "results": results,
    }


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
