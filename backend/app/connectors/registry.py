from typing import Type

from app.connectors.base import (
    BaseFileConnector,
)
from app.connectors.exceptions import (
    ConnectorNotFoundError,
)


class ConnectorRegistry:
    _connectors: dict[
        str,
        Type[BaseFileConnector],
    ] = {}

    @classmethod
    def register(
        cls,
        connector_type: str,
    ):
        normalized_type = (
            connector_type.strip().upper()
        )

        def decorator(
            connector_class: Type[
                BaseFileConnector
            ],
        ):
            if (
                normalized_type
                in cls._connectors
            ):
                raise ValueError(
                    "Connector already registered: "
                    f"{normalized_type}"
                )

            connector_class.connector_type = (
                normalized_type
            )

            cls._connectors[
                normalized_type
            ] = connector_class

            return connector_class

        return decorator

    @classmethod
    def get_connector_class(
        cls,
        connector_type: str,
    ) -> Type[BaseFileConnector]:
        normalized_type = (
            connector_type.strip().upper()
        )

        connector_class = (
            cls._connectors.get(
                normalized_type
            )
        )

        if connector_class is None:
            raise ConnectorNotFoundError(
                "Unsupported connector type: "
                f"{normalized_type}"
            )

        return connector_class

    @classmethod
    def available_connectors(
        cls,
    ) -> list[str]:
        return sorted(
            cls._connectors.keys()
        )

    @classmethod
    def connector_catalog(
        cls,
    ) -> list[dict]:
        catalog = []

        for connector_type in (
            cls.available_connectors()
        ):
            connector_class = (
                cls._connectors[
                    connector_type
                ]
            )

            catalog.append(
                {
                    "type": connector_type,
                    "displayName": getattr(
                        connector_class,
                        "display_name",
                        connector_type,
                    ),
                    "description": getattr(
                        connector_class,
                        "description",
                        "",
                    ),
                    "configurationSchema": getattr(
                        connector_class,
                        "configuration_schema",
                        {
                            "fields": [],
                        },
                    ),
                }
            )

        return catalog