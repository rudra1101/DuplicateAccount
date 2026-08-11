from datetime import datetime
from pathlib import Path

from app.connectors.base import (
    BaseFileConnector,
    ConnectionTestResult,
    ConnectorFile,
)
from app.connectors.exceptions import (
    ConnectorConfigurationError,
    ConnectorFileNotFoundError,
)
from app.connectors.registry import (
    ConnectorRegistry,
)


@ConnectorRegistry.register("LOCAL")
class LocalFileConnector(
    BaseFileConnector
):
    display_name = "Local Folder"

    description = (
        "Read delimited account files from "
        "a folder accessible to the backend server."
    )

    configuration_schema = {
        "fields": [
            {
                "name": "folderPath",
                "label": "Folder Path",
                "type": "text",
                "required": True,
                "placeholder": (
                    "C:\\IdentityFiles\\Incoming"
                ),
            },
            {
                "name": "filePattern",
                "label": "File Pattern",
                "type": "text",
                "required": True,
                "default": "*.csv",
                "placeholder": "accounts_*.csv",
            },
            {
                "name": "selectionStrategy",
                "label": "File Selection",
                "type": "select",
                "required": True,
                "default": "LATEST",
                "options": [
                    {
                        "label": "Latest file",
                        "value": "LATEST",
                    },
                    {
                        "label": "Oldest file",
                        "value": "OLDEST",
                    },
                ],
            },
            {
                "name": "delimiter",
                "label": "Delimiter",
                "type": "select",
                "required": True,
                "default": ",",
                "options": [
                    {
                        "label": "Comma",
                        "value": ",",
                    },
                    {
                        "label": "Pipe",
                        "value": "|",
                    },
                    {
                        "label": "Semicolon",
                        "value": ";",
                    },
                    {
                        "label": "Tab",
                        "value": "\t",
                    },
                ],
            },
            {
                "name": "encoding",
                "label": "Encoding",
                "type": "select",
                "required": True,
                "default": "utf-8-sig",
                "options": [
                    {
                        "label": "UTF-8",
                        "value": "utf-8-sig",
                    },
                    {
                        "label": "UTF-8",
                        "value": "utf-8",
                    },
                ],
            },
        ],
    }

    def validate_configuration(
        self,
    ) -> None:
        folder_path = (
            self.configuration.get(
                "folderPath"
            )
        )

        file_pattern = (
            self.configuration.get(
                "filePattern"
            )
        )

        if not folder_path:
            raise (
                ConnectorConfigurationError(
                    "folderPath is required."
                )
            )

        if not file_pattern:
            raise (
                ConnectorConfigurationError(
                    "filePattern is required."
                )
            )

    def test_connection(
        self,
    ) -> ConnectionTestResult:
        self.validate_configuration()

        folder = Path(
            self.configuration[
                "folderPath"
            ]
        )

        if not folder.exists():
            return ConnectionTestResult(
                success=False,
                message=(
                    "Configured folder "
                    "does not exist."
                ),
                details={
                    "folderPath": str(
                        folder
                    ),
                },
            )

        if not folder.is_dir():
            return ConnectionTestResult(
                success=False,
                message=(
                    "Configured path is "
                    "not a directory."
                ),
                details={
                    "folderPath": str(
                        folder
                    ),
                },
            )

        pattern = self.configuration[
            "filePattern"
        ]

        matching_files = [
            path.name
            for path in folder.glob(
                pattern
            )
            if path.is_file()
        ]

        return ConnectionTestResult(
            success=True,
            message=(
                "Local folder is accessible."
            ),
            details={
                "folderPath": str(folder),
                "matchingFileCount": len(
                    matching_files
                ),
                "matchingFiles": (
                    matching_files[:10]
                ),
            },
        )

    def fetch_file(
        self,
    ) -> ConnectorFile:
        self.validate_configuration()

        folder = Path(
            self.configuration[
                "folderPath"
            ]
        )

        if (
            not folder.exists()
            or not folder.is_dir()
        ):
            raise (
                ConnectorFileNotFoundError(
                    "Configured local folder "
                    "is not available."
                )
            )

        pattern = self.configuration[
            "filePattern"
        ]

        matched_files = [
            path
            for path in folder.glob(
                pattern
            )
            if path.is_file()
        ]

        if not matched_files:
            raise (
                ConnectorFileNotFoundError(
                    "No files matched pattern: "
                    f"{pattern}"
                )
            )

        strategy = (
            self.configuration.get(
                "selectionStrategy",
                "LATEST",
            )
            .strip()
            .upper()
        )

        if strategy == "OLDEST":
            selected_file = min(
                matched_files,
                key=lambda item: (
                    item.stat().st_mtime
                ),
            )
        else:
            selected_file = max(
                matched_files,
                key=lambda item: (
                    item.stat().st_mtime
                ),
            )

        stat = selected_file.stat()

        return ConnectorFile(
            content=selected_file.read_bytes(),
            filename=selected_file.name,
            source_path=str(
                selected_file.resolve()
            ),
            size=stat.st_size,
            modified_at=(
                datetime.fromtimestamp(
                    stat.st_mtime
                )
            ),
            metadata={
                "connectorType": "LOCAL",
            },
        )