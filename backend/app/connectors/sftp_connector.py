import io
from datetime import datetime

import paramiko

from app.connectors.base import (
    BaseFileConnector,
    ConnectionTestResult,
    ConnectorFile,
)
from app.connectors.exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorFileNotFoundError,
)
from app.connectors.registry import ConnectorRegistry


@ConnectorRegistry.register("SFTP")
class SftpConnector(BaseFileConnector):

    def __init__(
        self,
        configuration,
        secrets=None,
    ):
        super().__init__(
            configuration,
            secrets,
        )

        self._transport = None
        self._client = None

    def validate_configuration(self) -> None:
        required_fields = [
            "host",
            "username",
            "remoteDirectory",
            "filePattern",
        ]

        missing = [
            field
            for field in required_fields
            if not self.configuration.get(field)
        ]

        if missing:
            raise ConnectorConfigurationError(
                "Missing SFTP fields: "
                + ", ".join(missing)
            )

        if not self.secrets.get("password"):
            raise ConnectorConfigurationError(
                "SFTP password is required."
            )

    def _connect(self) -> None:
        self.validate_configuration()

        try:
            self._transport = paramiko.Transport(
                (
                    self.configuration["host"],
                    int(
                        self.configuration.get(
                            "port",
                            22,
                        )
                    ),
                )
            )

            self._transport.connect(
                username=self.configuration[
                    "username"
                ],
                password=self.secrets["password"],
            )

            self._client = (
                paramiko.SFTPClient.from_transport(
                    self._transport
                )
            )

        except Exception as exc:
            raise ConnectorConnectionError(
                f"SFTP connection failed: {exc}"
            ) from exc

    def test_connection(
        self,
    ) -> ConnectionTestResult:
        try:
            self._connect()

            self._client.listdir(
                self.configuration[
                    "remoteDirectory"
                ]
            )

            return ConnectionTestResult(
                success=True,
                message="SFTP connection succeeded.",
            )

        except Exception as exc:
            return ConnectionTestResult(
                success=False,
                message=str(exc),
            )

        finally:
            self.close()

    def fetch_file(self) -> ConnectorFile:
        self._connect()

        remote_directory = self.configuration[
            "remoteDirectory"
        ]

        file_pattern = self.configuration[
            "filePattern"
        ]

        import fnmatch

        matching_files = []

        for attributes in self._client.listdir_attr(
            remote_directory
        ):
            if fnmatch.fnmatch(
                attributes.filename,
                file_pattern,
            ):
                matching_files.append(attributes)

        if not matching_files:
            raise ConnectorFileNotFoundError(
                "No matching SFTP file was found."
            )

        selected = max(
            matching_files,
            key=lambda item: item.st_mtime,
        )

        remote_path = (
            f"{remote_directory.rstrip('/')}/"
            f"{selected.filename}"
        )

        buffer = io.BytesIO()

        self._client.getfo(
            remote_path,
            buffer,
        )

        return ConnectorFile(
            content=buffer.getvalue(),
            filename=selected.filename,
            source_path=remote_path,
            size=selected.st_size,
            modified_at=datetime.fromtimestamp(
                selected.st_mtime
            ),
            metadata={
                "connectorType": "SFTP",
                "host": self.configuration["host"],
            },
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

        if self._transport is not None:
            self._transport.close()
            self._transport = None