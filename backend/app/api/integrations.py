import csv

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import require_any_permission, require_permission
from app.connectors.exceptions import ConnectorError
from app.database.session import get_db
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationUpdate,
    SchemaDetectionRequest,
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
    test_integration_authentication,
    update_integration,
)
from app.services.schema_detection_service import detect_delimited_schema

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.post("/detect-schema")
def detect_schema(
    payload: SchemaDetectionRequest,
    _user=Depends(require_any_permission("integration.create", "integration.edit")),
):
    try:
        return detect_delimited_schema(
            connector_type=payload.connectorType,
            configuration=payload.configuration,
        )
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (UnicodeError, csv.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to detect schema: {exc}") from exc


@router.post("/{integration_id}/run")
def run_now(
    integration_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.run")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    if not integration.enabled:
        raise HTTPException(status_code=400, detail="The integration is disabled. Enable it before running.")
    try:
        return run_integration(db=db, integration=integration)
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Integration execution failed: {exc}") from exc


@router.get("/{integration_id}/executions")
def execution_history(
    integration_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    return get_integration_executions(
        db=db,
        integration_id=integration_id,
        limit=max(1, min(limit, 100)),
    )


@router.get("/connector-types")
def connector_types(_user=Depends(require_permission("integration.create"))):
    return list_connector_types()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create(
    payload: IntegrationCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.create")),
):
    try:
        return integration_to_dict(create_integration(db=db, payload=payload))
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An integration with this name already exists.") from exc
    except ConnectorError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/")
def list_all(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100, alias="pageSize"),
    search: str = Query(default=""),
    enabled: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    integrations, total = get_integrations(
        db,
        page=page,
        page_size=page_size,
        search=search,
        enabled=enabled,
    )
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "items": [integration_to_dict(item) for item in integrations],
    }


@router.get("/{integration_id}")
def get_one(
    integration_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    return integration_to_dict(integration)


@router.put("/{integration_id}")
def update(
    integration_id: int,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.edit")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    try:
        return integration_to_dict(update_integration(db=db, integration=integration, payload=payload))
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An integration with this name already exists.") from exc
    except ConnectorError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    integration_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.delete")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    delete_integration(db=db, integration=integration)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{integration_id}/test-authentication")
def test_authentication(
    integration_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.test")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    try:
        return test_integration_authentication(integration)
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Unable to test authentication.") from exc


@router.post("/{integration_id}/test")
def test(
    integration_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.test")),
):
    integration = get_integration(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    try:
        return test_integration(integration)
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Unable to test integration.") from exc
