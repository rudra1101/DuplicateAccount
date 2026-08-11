from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.base import (
    BaseAITool,
)
from app.services.operations_service import (
    get_operation,
    get_operations,
    get_operations_summary,
)


class GetOperationsSummaryTool(
    BaseAITool
):
    name = "get_operations_summary"

    description = (
        "Get the total number of integration executions "
        "and counts for running, completed, and failed jobs."
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
        return get_operations_summary(
            db
        )


class SearchOperationsTool(
    BaseAITool
):
    name = "search_operations"

    description = (
        "Search manual and scheduled integration "
        "executions by status, integration, filename, "
        "path, or error message."
    )

    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": [
                    "string",
                    "null",
                ],
                "enum": [
                    "RUNNING",
                    "COMPLETED",
                    "FAILED",
                    None,
                ],
            },
            "integration_id": {
                "type": [
                    "integer",
                    "null",
                ],
            },
            "search": {
                "type": [
                    "string",
                    "null",
                ],
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": [
            "status",
            "integration_id",
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
        return get_operations(
            db=db,
            status=arguments.get(
                "status"
            ),
            integration_id=arguments.get(
                "integration_id"
            ),
            search=arguments.get(
                "search"
            ),
            limit=int(
                arguments.get(
                    "limit",
                    20,
                )
            ),
            offset=0,
        )


class GetExecutionDetailsTool(
    BaseAITool
):
    name = "get_execution_details"

    description = (
        "Get complete details for one integration "
        "execution using its execution ID."
    )

    parameters = {
        "type": "object",
        "properties": {
            "execution_id": {
                "type": "integer",
                "minimum": 1,
            },
        },
        "required": [
            "execution_id",
        ],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        execution_id = int(
            arguments["execution_id"]
        )

        result = get_operation(
            db=db,
            execution_id=execution_id,
        )

        if result is None:
            return {
                "found": False,
                "message": (
                    "Execution was not found."
                ),
            }

        return {
            "found": True,
            "execution": result,
        }