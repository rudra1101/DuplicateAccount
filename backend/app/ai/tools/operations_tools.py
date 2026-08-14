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
                func.lower(IntegrationRecord.name)
                == normalized,
                func.lower(IntegrationRecord.name)
                .like(f"%{normalized}%"),
                func.lower(IntegrationRecord.connector_type)
                .like(f"%{normalized}%"),
            )
        )
        .order_by(IntegrationRecord.name.asc())
        .limit(1)
    ).first()

    return row.id if row else None


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
                "enum": [
                    "RUNNING",
                    "COMPLETED",
                    "FAILED",
                    None,
                ],
            },
            "integration": {
                "type": ["string", "null"],
                "description": (
                    "Integration name, connector alias, or numeric ID."
                ),
            },
            "search": {"type": ["string", "null"]},
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": [
            "status",
            "integration",
            "search",
            "limit",
        ],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        integration_value = arguments.get("integration")
        integration_id = _resolve_integration_id(
            db,
            integration_value,
        )

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
            limit=min(
                max(int(arguments.get("limit", 20) or 20), 1),
                100,
            ),
            offset=0,
        )

        return {
            "found": bool(result),
            "count": len(result),
            "operations": result,
        }


class GetExecutionDetailsTool(BaseAITool):
    name = "get_execution_details"

    description = (
        "Get complete details for one integration execution using "
        "its execution ID."
    )

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

        return {
            "found": True,
            "execution": result,
        }


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
                "enum": [
                    "RUNNING",
                    "COMPLETED",
                    "FAILED",
                    None,
                ],
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
        integration_id = _resolve_integration_id(
            db,
            integration_value,
        )

        if integration_value and integration_id is None:
            return {
                "found": False,
                "message": "Integration was not found.",
            }

        statement = (
            select(JobExecutionRecord, IntegrationRecord)
            .join(
                IntegrationRecord,
                IntegrationRecord.id
                == JobExecutionRecord.integration_id,
            )
        )

        if integration_id is not None:
            statement = statement.where(
                JobExecutionRecord.integration_id
                == integration_id
            )

        status = arguments.get("status")
        if status:
            statement = statement.where(
                JobExecutionRecord.status
                == str(status).upper()
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

        return {
            "found": True,
            "execution": {
                "id": execution.id,
                "integrationId": integration.id,
                "integrationName": integration.name,
                "scanId": execution.scan_id,
                "status": execution.status,
                "sourceFileName": execution.source_file_name,
                "sourcePath": execution.source_path,
                "accountsScanned": execution.accounts_scanned,
                "duplicateGroups": execution.duplicate_groups,
                "duplicateAccounts": execution.duplicate_accounts,
                "errorMessage": execution.error_message,
                "startedAt": (
                    execution.started_at.isoformat()
                    if execution.started_at
                    else None
                ),
                "completedAt": (
                    execution.completed_at.isoformat()
                    if execution.completed_at
                    else None
                ),
            },
        }
