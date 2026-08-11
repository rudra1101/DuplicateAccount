from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.operations_service import (
    get_operation,
    get_operations,
    get_operations_summary,
    retry_execution,
)


router = APIRouter(
    prefix="/operations",
    tags=["Operations Center"],
)


@router.get("/summary")
def operations_summary(
    db: Session = Depends(get_db),
):
    try:
        return get_operations_summary(db)

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load operations summary."
            ),
        ) from exc


@router.get("/")
def list_operations(
    status: str | None = Query(
        default=None
    ),
    integrationId: int | None = Query(
        default=None
    ),
    search: str | None = Query(
        default=None
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):
    try:
        return get_operations(
            db=db,
            status=status,
            integration_id=integrationId,
            search=search,
            limit=limit,
            offset=offset,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load job executions."
            ),
        ) from exc


@router.get("/{execution_id}")
def operation_details(
    execution_id: int,
    db: Session = Depends(get_db),
):
    result = get_operation(
        db=db,
        execution_id=execution_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Execution not found.",
        )

    return result


@router.post(
    "/{execution_id}/retry"
)
def retry_operation(
    execution_id: int,
    db: Session = Depends(get_db),
):
    try:
        return retry_execution(
            db=db,
            execution_id=execution_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Retry execution failed: "
                f"{exc}"
            ),
        ) from exc