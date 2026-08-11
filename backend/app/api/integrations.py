from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)
from sqlalchemy.orm import Session

from app.connectors.exceptions import (
    ConnectorError,
)
from app.database.session import get_db
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationUpdate,
)
from app.services.integration_service import (
    create_integration,
    delete_integration,
    get_integration,
    get_integration_executions,
    get_integrations,
    integration_to_dict,
    list_connector_types,
    run_integration,
    test_integration,
    update_integration,
)

router = APIRouter(
    prefix="/integrations",
    tags=["Integrations"],
)

@router.post(
    "/{integration_id}/run"
)
def run_now(
    integration_id: int,
    db: Session = Depends(get_db),
):
    integration = get_integration(
        db,
        integration_id,
    )

    if integration is None:
        raise HTTPException(
            status_code=404,
            detail="Integration not found.",
        )

    if not integration.enabled:
        raise HTTPException(
            status_code=400,
            detail=(
                "The integration is disabled. "
                "Enable it before running."
            ),
        )

    try:
        return run_integration(
            db=db,
            integration=integration,
        )

    except ConnectorError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Integration execution failed: "
                f"{exc}"
            ),
        ) from exc


@router.get(
    "/{integration_id}/executions"
)
def execution_history(
    integration_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    integration = get_integration(
        db,
        integration_id,
    )

    if integration is None:
        raise HTTPException(
            status_code=404,
            detail="Integration not found.",
        )

    safe_limit = max(
        1,
        min(limit, 100),
    )

    return get_integration_executions(
        db=db,
        integration_id=integration_id,
        limit=safe_limit,
    )

@router.get("/connector-types")
def connector_types():
    return list_connector_types()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
def create(
    payload: IntegrationCreate,
    db: Session = Depends(get_db),
):
    try:
        integration = create_integration(
            db=db,
            payload=payload,
        )

        return integration_to_dict(
            integration
        )

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "An integration with this "
                "name already exists."
            ),
        ) from exc

    except ConnectorError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/")
def list_all(
    db: Session = Depends(get_db),
):
    integrations = get_integrations(db)

    return [
        integration_to_dict(item)
        for item in integrations
    ]


@router.get("/{integration_id}")
def get_one(
    integration_id: int,
    db: Session = Depends(get_db),
):
    integration = get_integration(
        db,
        integration_id,
    )

    if integration is None:
        raise HTTPException(
            status_code=404,
            detail="Integration not found.",
        )

    return integration_to_dict(
        integration
    )


@router.put("/{integration_id}")
def update(
    integration_id: int,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
):
    integration = get_integration(
        db,
        integration_id,
    )

    if integration is None:
        raise HTTPException(
            status_code=404,
            detail="Integration not found.",
        )

    try:
        updated = update_integration(
            db=db,
            integration=integration,
            payload=payload,
        )

        return integration_to_dict(
            updated
        )

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "An integration with this "
                "name already exists."
            ),
        ) from exc

    except ConnectorError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete(
    integration_id: int,
    db: Session = Depends(get_db),
):
    integration = get_integration(
        db,
        integration_id,
    )

    if integration is None:
        raise HTTPException(
            status_code=404,
            detail="Integration not found.",
        )

    delete_integration(
        db=db,
        integration=integration,
    )

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )


@router.post(
    "/{integration_id}/test"
)
def test(
    integration_id: int,
    db: Session = Depends(get_db),
):
    integration = get_integration(
        db,
        integration_id,
    )

    if integration is None:
        raise HTTPException(
            status_code=404,
            detail="Integration not found.",
        )

    try:
        return test_integration(
            integration
        )

    except ConnectorError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to test integration."
            ),
        ) from exc