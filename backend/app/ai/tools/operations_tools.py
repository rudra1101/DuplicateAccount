from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.services.operations_service import (
    get_operation,
    get_operations,
    get_operations_summary,
    operation_to_dict,
)


def _resolve_integration_id(
    db: Session,
    value: Any,
) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None

    if text.isdigit():
        return int(text)

    normalized = text.lower()
    aliases = {
        "ad": "active directory",
        "azure ad": "entra",
        "azure active directory": "entra",
        "snow": "servicenow",
        "service now": "servicenow",
    }
    normalized = aliases.get(normalized, normalized)

    row = db.scalars(
        select(IntegrationRecord)
        .where(
            or_(
                func.lower(IntegrationRecord.name) == normalized,
                func.lower(IntegrationRecord.name).like(f"%{normalized}%"),
                func.lower(IntegrationRecord.connector_type).like(f"%{normalized}%"),
            )
        )
        .order_by(IntegrationRecord.name.asc())
        .limit(1)
    ).first()

    return row.id if row else None


def _execution_message(execution: dict[str, Any]) -> str:
    """Render persisted execution facts into a deterministic Rudrix summary."""

    execution_id = execution.get("executionId") or execution.get("id")
    integration_name = (
        execution.get("integrationName")
        or (
            f"Integration {execution.get('integrationId')}"
            if execution.get("integrationId") is not None
            else "Integration"
        )
    )
    status = str(execution.get("status") or "UNKNOWN").upper()
    aggregation_type = str(execution.get("aggregationType") or "").upper()

    run_label = f"{aggregation_type.lower()} aggregation" if aggregation_type else "execution"
    identity = f" (execution {execution_id})" if execution_id is not None else ""
    parts = [f"{integration_name} {run_label}{identity} is {status}."]

    accounts_scanned = execution.get("accountsScanned")
    if accounts_scanned is not None:
        parts.append(f"Accounts scanned: {accounts_scanned}.")

    inventory_parts: list[str] = []
    for key, label in (
        ("accountsCreated", "created"),
        ("accountsUpdated", "updated"),
        ("accountsUnchanged", "unchanged"),
        ("accountsDeleted", "deleted"),
    ):
        value = execution.get(key)
        if value is not None:
            inventory_parts.append(f"{label}: {value}")
    if inventory_parts:
        parts.append("Account changes — " + ", ".join(inventory_parts) + ".")

    duplicate_groups = execution.get("duplicateGroups")
    duplicate_accounts = execution.get("duplicateAccounts")
    if duplicate_groups is not None or duplicate_accounts is not None:
        parts.append(
            "Duplicates — groups: "
            f"{duplicate_groups if duplicate_groups is not None else 0}, accounts: "
            f"{duplicate_accounts if duplicate_accounts is not None else 0}."
        )

    error_message = str(execution.get("errorMessage") or "").strip()
    if error_message:
        parts.append(f"Failure reason: {error_message}")

    completed_at = execution.get("completedAt")
    if completed_at:
        parts.append(f"Completed at: {completed_at}.")

    return " ".join(parts)


def _execution_result(execution: dict[str, Any]) -> dict[str, Any]:
    return {
        "found": True,
        "resultType": "integration_execution",
        "execution": execution,
        "message": _execution_message(execution),
    }


class GetOperationsSummaryTool(BaseAITool):
    name = "get_operations_summary"

    description = (
        "Get total integration execution counts and counts for running, "
        "completed, and failed jobs."
    )

    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        return get_operations_summary(db)


class SearchOperationsTool(BaseAITool):
    name = "search_operations"

    description = (
        "Search manual and scheduled integration executions by status, "
        "integration name or ID, filename, path, or error message."
    )

    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": ["string", "null"],
                "enum": ["RUNNING", "COMPLETED", "FAILED", None],
            },
            "integration": {
                "type": ["string", "null"],
                "description": "Integration name, connector alias, or numeric ID.",
            },
            "search": {"type": ["string", "null"]},
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": ["status", "integration", "search", "limit"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        integration_value = arguments.get("integration")
        integration_id = _resolve_integration_id(db, integration_value)

        if integration_value and integration_id is None:
            return {
                "found": False,
                "count": 0,
                "operations": [],
                "message": "Integration was not found.",
            }

        result = get_operations(
            db=db,
            status=arguments.get("status"),
            integration_id=integration_id,
            search=arguments.get("search"),
            limit=min(max(int(arguments.get("limit", 20) or 20), 1), 100),
            offset=0,
        )

        return {
            "found": bool(result),
            "count": len(result),
            "operations": result,
        }


class GetExecutionDetailsTool(BaseAITool):
    name = "get_execution_details"

    description = "Get complete details for one integration execution using its execution ID."

    parameters = {
        "type": "object",
        "properties": {
            "execution_id": {
                "type": "integer",
                "minimum": 1,
            },
        },
        "required": ["execution_id"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        result = get_operation(
            db=db,
            execution_id=int(arguments["execution_id"]),
        )

        if result is None:
            return {
                "found": False,
                "message": "Execution was not found.",
            }

        return _execution_result(result)


class GetLatestExecutionTool(BaseAITool):
    name = "get_latest_execution"

    description = (
        "Get the most recent integration execution, optionally filtered "
        "by integration and execution status."
    )

    parameters = {
        "type": "object",
        "properties": {
            "integration": {"type": ["string", "null"]},
            "status": {
                "type": ["string", "null"],
                "enum": ["RUNNING", "COMPLETED", "FAILED", None],
            },
        },
        "required": ["integration", "status"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        integration_value = arguments.get("integration")
        integration_id = _resolve_integration_id(db, integration_value)

        if integration_value and integration_id is None:
            return {
                "found": False,
                "message": "Integration was not found.",
            }

        statement = (
            select(JobExecutionRecord, IntegrationRecord)
            .join(
                IntegrationRecord,
                IntegrationRecord.id == JobExecutionRecord.integration_id,
            )
        )

        if integration_id is not None:
            statement = statement.where(
                JobExecutionRecord.integration_id == integration_id
            )

        status = arguments.get("status")
        if status:
            statement = statement.where(
                JobExecutionRecord.status == str(status).upper()
            )

        row = db.execute(
            statement.order_by(
                JobExecutionRecord.started_at.desc(),
                JobExecutionRecord.id.desc(),
            ).limit(1)
        ).first()

        if row is None:
            return {
                "found": False,
                "message": "No matching execution was found.",
            }

        execution, integration = row
        return _execution_result(operation_to_dict(execution, integration))
