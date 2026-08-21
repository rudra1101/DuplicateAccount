from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.factory import (
    ConnectorFactory,
)
from app.connectors.registry import (
    ConnectorRegistry,
)
from app.db_models.integration import (
    IntegrationRecord,
)
from app.db_models.job_execution import (
    JobExecutionRecord,
)
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationUpdate,
)
from app.services.integration_ingestion_service import (
    execute_integration,
    execution_to_dict,
)


def integration_to_dict(
    integration: IntegrationRecord,
) -> dict:
    return {
        "id": integration.id,
        "name": integration.name,
        "connectorType": integration.connector_type,
        "description": integration.description,
        "configuration": integration.configuration or {},
        "enabled": integration.enabled,
        "createdAt": integration.created_at.isoformat() if integration.created_at else None,
        "updatedAt": integration.updated_at.isoformat() if integration.updated_at else None,
    }


def list_connector_types() -> list[dict]:
    return ConnectorRegistry.connector_catalog()


def create_integration(
    db: Session,
    payload: IntegrationCreate,
) -> IntegrationRecord:
    connector_type = payload.connectorType.strip().upper()
    connector = ConnectorFactory.create(
        connector_type=connector_type,
        configuration=payload.configuration,
    )
    connector.validate_configuration()

    integration = IntegrationRecord(
        name=payload.name.strip(),
        connector_type=connector_type,
        description=payload.description,
        configuration=payload.configuration or {},
        enabled=payload.enabled,
    )

    try:
        db.add(integration)
        db.commit()
        db.refresh(integration)
    except Exception:
        db.rollback()
        raise

    return integration


def get_integrations(
    db: Session,
) -> list[IntegrationRecord]:
    statement = (
        select(IntegrationRecord)
        .order_by(
            IntegrationRecord.created_at.desc(),
            IntegrationRecord.id.desc(),
        )
    )
    return list(db.scalars(statement).all())


def get_integration(
    db: Session,
    integration_id: int,
) -> IntegrationRecord | None:
    return db.get(IntegrationRecord, integration_id)


def update_integration(
    db: Session,
    integration: IntegrationRecord,
    payload: IntegrationUpdate,
) -> IntegrationRecord:
    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data:
        integration.name = str(update_data["name"] or "").strip()
        if not integration.name:
            raise ValueError("Integration name cannot be empty.")

    if "description" in update_data:
        integration.description = update_data["description"]

    if "enabled" in update_data:
        integration.enabled = bool(update_data["enabled"])

    if "configuration" in update_data:
        new_configuration = update_data["configuration"] or {}
        connector = ConnectorFactory.create(
            connector_type=integration.connector_type,
            configuration=new_configuration,
        )
        connector.validate_configuration()
        integration.configuration = new_configuration

    try:
        db.commit()
        db.refresh(integration)
    except Exception:
        db.rollback()
        raise

    return integration


def delete_integration(
    db: Session,
    integration: IntegrationRecord,
) -> None:
    try:
        db.delete(integration)
        db.commit()
    except Exception:
        db.rollback()
        raise


def _test_result_to_dict(integration: IntegrationRecord, result) -> dict:
    return {
        "integrationId": integration.id,
        "connectorType": integration.connector_type,
        "success": result.success,
        "message": result.message,
        "details": result.details or {},
    }


def test_integration_authentication(
    integration: IntegrationRecord,
) -> dict:
    connector = ConnectorFactory.create(
        connector_type=integration.connector_type,
        configuration=integration.configuration or {},
    )

    with connector:
        test_authentication = getattr(connector, "test_authentication", None)
        if callable(test_authentication):
            result = test_authentication()
        else:
            result = connector.test_connection()

    return _test_result_to_dict(integration, result)


def test_integration(
    integration: IntegrationRecord,
) -> dict:
    connector = ConnectorFactory.create(
        connector_type=integration.connector_type,
        configuration=integration.configuration or {},
    )

    with connector:
        result = connector.test_connection()

    return _test_result_to_dict(integration, result)


def run_integration(
    db: Session,
    integration: IntegrationRecord,
) -> dict:
    execution = execute_integration(
        db=db,
        integration=integration,
    )
    return execution_to_dict(execution)


def get_integration_executions(
    db: Session,
    integration_id: int,
    limit: int = 20,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 100))
    statement = (
        select(JobExecutionRecord)
        .where(JobExecutionRecord.integration_id == integration_id)
        .order_by(
            JobExecutionRecord.started_at.desc(),
            JobExecutionRecord.id.desc(),
        )
        .limit(safe_limit)
    )
    executions = db.scalars(statement).all()
    return [execution_to_dict(execution) for execution in executions]
