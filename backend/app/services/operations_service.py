from typing import Any

from sqlalchemy import (
    case,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.services.integration_ingestion_service import (
    execute_integration,
    execution_to_dict,
)


VALID_STATUSES = {
    "RUNNING",
    "COMPLETED",
    "FAILED",
}


def operation_to_dict(
    execution: JobExecutionRecord,
    integration: IntegrationRecord,
) -> dict[str, Any]:
    data = execution_to_dict(execution)

    data.update(
        {
            "integrationName": integration.name,
            "connectorType": integration.connector_type,
        }
    )

    return data


def get_operations_summary(
    db: Session,
) -> dict[str, int]:
    statement = select(
        func.count(
            JobExecutionRecord.id
        ).label("total"),

        func.coalesce(
            func.sum(
                case(
                    (
                        JobExecutionRecord.status
                        == "RUNNING",
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("running"),

        func.coalesce(
            func.sum(
                case(
                    (
                        JobExecutionRecord.status
                        == "COMPLETED",
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("completed"),

        func.coalesce(
            func.sum(
                case(
                    (
                        JobExecutionRecord.status
                        == "FAILED",
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("failed"),
    )

    row = db.execute(statement).one()

    return {
        "total": int(row.total or 0),
        "running": int(row.running or 0),
        "completed": int(row.completed or 0),
        "failed": int(row.failed or 0),
    }


def get_operations(
    db: Session,
    *,
    status: str | None = None,
    integration_id: int | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    statement = (
        select(
            JobExecutionRecord,
            IntegrationRecord,
        )
        .join(
            IntegrationRecord,
            IntegrationRecord.id
            == JobExecutionRecord.integration_id,
        )
    )

    if status:
        normalized_status = (
            status.strip().upper()
        )

        if normalized_status not in VALID_STATUSES:
            raise ValueError(
                "Unsupported execution status: "
                f"{status}"
            )

        statement = statement.where(
            JobExecutionRecord.status
            == normalized_status
        )

    if integration_id is not None:
        statement = statement.where(
            JobExecutionRecord.integration_id
            == integration_id
        )

    if search and search.strip():
        search_value = (
            f"%{search.strip()}%"
        )

        statement = statement.where(
            or_(
                IntegrationRecord.name.ilike(
                    search_value
                ),
                JobExecutionRecord
                .source_file_name
                .ilike(search_value),
                JobExecutionRecord
                .source_path
                .ilike(search_value),
                JobExecutionRecord
                .error_message
                .ilike(search_value),
            )
        )

    statement = (
        statement
        .order_by(
            JobExecutionRecord
            .started_at.desc(),
            JobExecutionRecord.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    rows = db.execute(statement).all()

    return [
        operation_to_dict(
            execution=execution,
            integration=integration,
        )
        for execution, integration in rows
    ]


def get_operation(
    db: Session,
    execution_id: int,
) -> dict[str, Any] | None:
    statement = (
        select(
            JobExecutionRecord,
            IntegrationRecord,
        )
        .join(
            IntegrationRecord,
            IntegrationRecord.id
            == JobExecutionRecord.integration_id,
        )
        .where(
            JobExecutionRecord.id
            == execution_id
        )
    )

    row = db.execute(
        statement
    ).first()

    if row is None:
        return None

    execution, integration = row

    return operation_to_dict(
        execution=execution,
        integration=integration,
    )


def retry_execution(
    db: Session,
    execution_id: int,
) -> dict[str, Any]:
    execution = db.get(
        JobExecutionRecord,
        execution_id,
    )

    if execution is None:
        raise ValueError(
            "Execution not found."
        )

    if execution.status != "FAILED":
        raise ValueError(
            "Only failed executions can be retried."
        )

    integration = db.get(
        IntegrationRecord,
        execution.integration_id,
    )

    if integration is None:
        raise ValueError(
            "The integration associated with this "
            "execution no longer exists."
        )

    if not integration.enabled:
        raise ValueError(
            "The integration is disabled."
        )

    new_execution = execute_integration(
        db=db,
        integration=integration,
    )

    return operation_to_dict(
        execution=new_execution,
        integration=integration,
    )