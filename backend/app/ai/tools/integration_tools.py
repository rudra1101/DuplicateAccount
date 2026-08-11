from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.tools.base import (
    BaseAITool,
)
from app.db_models.integration import (
    IntegrationRecord,
)
from app.services.integration_service import (
    integration_to_dict,
)


class ListIntegrationsTool(
    BaseAITool
):
    name = "list_integrations"

    description = (
        "List configured account-source integrations, "
        "including connector type and enabled status."
    )

    parameters = {
        "type": "object",
        "properties": {
            "enabled_only": {
                "type": "boolean",
            },
        },
        "required": [
            "enabled_only",
        ],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        statement = select(
            IntegrationRecord
        ).order_by(
            IntegrationRecord.name.asc()
        )

        if arguments.get(
            "enabled_only",
            False,
        ):
            statement = statement.where(
                IntegrationRecord.enabled.is_(
                    True
                )
            )

        integrations = db.scalars(
            statement
        ).all()

        return [
            integration_to_dict(
                integration
            )
            for integration in integrations
        ]