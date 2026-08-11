from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar


@dataclass
class ConnectorFile:
    content: bytes
    filename: str
    source_path: str
    size: int
    modified_at: datetime | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ConnectionTestResult:
    success: bool
    message: str
    details: dict[str, Any] = field(
        default_factory=dict
    )


class BaseFileConnector(ABC):
    connector_type: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str] = ""
    configuration_schema: ClassVar[
        dict[str, Any]
    ] = {
        "fields": [],
    }

    def __init__(
        self,
        configuration: dict[str, Any],
        secrets: dict[str, str] | None = None,
    ):
        self.configuration = configuration
        self.secrets = secrets or {}

    @abstractmethod
    def validate_configuration(self) -> None:
        pass

    @abstractmethod
    def test_connection(
        self,
    ) -> ConnectionTestResult:
        pass

    @abstractmethod
    def fetch_file(self) -> ConnectorFile:
        pass

    def close(self) -> None:
        pass

    def __enter__(
        self,
    ) -> "BaseFileConnector":
        self.validate_configuration()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()