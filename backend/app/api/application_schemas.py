from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.schemas.application_schema import IntegrationApplicationsPayload
from app.services.application_schema_service import (
    get_applications_for_integration,
    replace_integration_applications,
)
from app.services.integration_service import get_integration


router = APIRouter(
    prefix="/integrations/{integration_id}/applications",
    tags=["Application Schemas"],
)


@router.get("/")
def list_applications(
    integration_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")

    return get_applications_for_integration(db, integration_id)


@router.put("/")
def replace_applications(
    integration_id: int,
    payload: IntegrationApplicationsPayload,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.edit")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")

    try:
        return replace_integration_applications(
            db=db,
            integration=integration,
            payload=payload,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Application names and schema attributes must be unique.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save application schemas.",
        ) from exc
