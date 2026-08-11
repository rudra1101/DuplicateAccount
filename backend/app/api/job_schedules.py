from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.db_models.integration import IntegrationRecord
from app.schemas.job_schedule import (
    JobScheduleCreate,
    JobScheduleUpdate,
)
from app.services.job_schedule_service import (
    create_schedule,
    delete_schedule,
    disable_schedule,
    enable_schedule,
    get_schedule_by_integration,
    schedule_to_dict,
    update_schedule,
)


router = APIRouter(
    prefix="/integrations",
    tags=["Integration Schedules"],
)


def get_integration_or_404(
    db: Session,
    integration_id: int,
) -> IntegrationRecord:
    integration = db.get(
        IntegrationRecord,
        integration_id,
    )

    if integration is None:
        raise HTTPException(
            status_code=404,
            detail="Integration not found.",
        )

    return integration


def get_schedule_or_404(
    db: Session,
    integration_id: int,
):
    schedule = get_schedule_by_integration(
        db=db,
        integration_id=integration_id,
    )

    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Schedule not found.",
        )

    return schedule


@router.post(
    "/{integration_id}/schedule",
    status_code=status.HTTP_201_CREATED,
)
def create_integration_schedule(
    integration_id: int,
    payload: JobScheduleCreate,
    db: Session = Depends(get_db),
):
    integration = get_integration_or_404(
        db,
        integration_id,
    )

    try:
        schedule = create_schedule(
            db=db,
            integration=integration,
            payload=payload,
        )

        return schedule_to_dict(
            schedule
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create schedule.",
        ) from exc


@router.get(
    "/{integration_id}/schedule"
)
def get_integration_schedule(
    integration_id: int,
    db: Session = Depends(get_db),
):
    get_integration_or_404(
        db,
        integration_id,
    )

    schedule = get_schedule_or_404(
        db,
        integration_id,
    )

    return schedule_to_dict(
        schedule
    )


@router.put(
    "/{integration_id}/schedule"
)
def update_integration_schedule(
    integration_id: int,
    payload: JobScheduleUpdate,
    db: Session = Depends(get_db),
):
    get_integration_or_404(
        db,
        integration_id,
    )

    schedule = get_schedule_or_404(
        db,
        integration_id,
    )

    try:
        updated = update_schedule(
            db=db,
            schedule=schedule,
            payload=payload,
        )

        return schedule_to_dict(
            updated
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to update schedule.",
        ) from exc


@router.post(
    "/{integration_id}/schedule/enable"
)
def enable_integration_schedule(
    integration_id: int,
    db: Session = Depends(get_db),
):
    get_integration_or_404(
        db,
        integration_id,
    )

    schedule = get_schedule_or_404(
        db,
        integration_id,
    )

    try:
        enabled_schedule = enable_schedule(
            db=db,
            schedule=schedule,
        )

        return schedule_to_dict(
            enabled_schedule
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/{integration_id}/schedule/disable"
)
def disable_integration_schedule(
    integration_id: int,
    db: Session = Depends(get_db),
):
    get_integration_or_404(
        db,
        integration_id,
    )

    schedule = get_schedule_or_404(
        db,
        integration_id,
    )

    disabled_schedule = disable_schedule(
        db=db,
        schedule=schedule,
    )

    return schedule_to_dict(
        disabled_schedule
    )


@router.delete(
    "/{integration_id}/schedule",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_integration_schedule(
    integration_id: int,
    db: Session = Depends(get_db),
):
    get_integration_or_404(
        db,
        integration_id,
    )

    schedule = get_schedule_or_404(
        db,
        integration_id,
    )

    delete_schedule(
        db=db,
        schedule=schedule,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )