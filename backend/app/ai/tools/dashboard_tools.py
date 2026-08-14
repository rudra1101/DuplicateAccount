from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.services.dashboard_service import (
    build_dashboard_response,
)


class GetDashboardSummaryTool(BaseAITool):
    name = "get_dashboard_summary"

    description = (
        "Get CURRENT system-wide IdentityAI dashboard metrics "
        "from the latest completed scan for each integration. "
        "Use this for general questions about total accounts, "
        "applications, integrations, duplicate groups, duplicate "
        "accounts, high-confidence matches, application statistics, "
        "latest scans, or overall platform status. "
        "For general questions such as 'how many high confidence "
        "matches do we have', use this tool instead of searching "
        "individual duplicate groups."
    )

    parameters = {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "enum": [
                    "daily",
                    "weekly",
                    "monthly",
                    "yearly",
                ],
                "description": (
                    "The dashboard reporting period."
                ),
            },
        },
        "required": [
            "period",
        ],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        period = str(
            arguments.get(
                "period",
                "daily",
            )
        ).strip().lower()

        return build_dashboard_response(
            db=db,
            period=period,
        )