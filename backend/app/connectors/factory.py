from typing import Any

from app.connectors.base import BaseFileConnector
from app.connectors.registry import ConnectorRegistry


class ConnectorFactory:
    @staticmethod
    def create(
        connector_type: str,
        configuration: dict[str, Any],
        secrets: dict[str, str] | None = None,
    ) -> BaseFileConnector:
        connector_class = (
            ConnectorRegistry.get_connector_class(
                connector_type
            )
        )

        return connector_class(
            configuration=configuration,
            secrets=secrets,
        )