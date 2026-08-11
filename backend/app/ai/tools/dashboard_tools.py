from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.services.dashboard_service import (
    build_dashboard_response,
)


class GetDashboardSummaryTool(BaseAITool):
    name = "get_dashboard_summary"

    description = (
        "Get duplicate-account dashboard metrics, "
        "latest scan information, application statistics, "
        "and scan trend data for a selected period."
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