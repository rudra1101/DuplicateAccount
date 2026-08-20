from __future__ import annotations

import csv
import io
import json
import ssl
from base64 import b64encode
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.connectors.base import BaseFileConnector, ConnectionTestResult, ConnectorFile
from app.connectors.exceptions import ConnectorConfigurationError, ConnectorError
from app.connectors.registry import ConnectorRegistry


@ConnectorRegistry.register("WEB_SERVICE")
class WebServiceConnector(BaseFileConnector):
    display_name = "Web Service (REST API)"

    description = (
        "Read account data from a REST API endpoint. JSON arrays or nested JSON "
        "arrays are converted into a tabular account feed for ingestion."
    )

    configuration_schema = {
        "fields": [
            {
                "name": "endpointUrl",
                "label": "Endpoint URL",
                "type": "text",
                "required": True,
                "placeholder": "https://api.example.com/v1/accounts",
                "helpText": "REST endpoint that returns account records as JSON.",
            },
            {
                "name": "method",
                "label": "HTTP Method",
                "type": "select",
                "required": True,
                "default": "GET",
                "options": [
                    {"label": "GET", "value": "GET"},
                    {"label": "POST", "value": "POST"},
                ],
            },
            {
                "name": "authType",
                "label": "Authentication",
                "type": "select",
                "required": True,
                "default": "NONE",
                "options": [
                    {"label": "None", "value": "NONE"},
                    {"label": "Bearer Token", "value": "BEARER"},
                    {"label": "Basic Authentication", "value": "BASIC"},
                    {"label": "API Key Header", "value": "API_KEY"},
                ],
            },
            {
                "name": "bearerToken",
                "label": "Bearer Token",
                "type": "password",
                "required": False,
                "helpText": "Required only when Authentication is Bearer Token.",
            },
            {
                "name": "username",
                "label": "Username",
                "type": "text",
                "required": False,
            },
            {
                "name": "password",
                "label": "Password",
                "type": "password",
                "required": False,
            },
            {
                "name": "apiKeyHeader",
                "label": "API Key Header",
                "type": "text",
                "required": False,
                "default": "X-API-Key",
            },
            {
                "name": "apiKeyValue",
                "label": "API Key Value",
                "type": "password",
                "required": False,
            },
            {
                "name": "headersJson",
                "label": "Additional Headers (JSON)",
                "type": "text",
                "required": False,
                "placeholder": "{\"Accept\":\"application/json\"}",
            },
            {
                "name": "requestBodyJson",
                "label": "Request Body (JSON)",
                "type": "text",
                "required": False,
                "placeholder": "{\"status\":\"active\"}",
                "helpText": "Optional JSON body, typically used with POST.",
            },
            {
                "name": "recordsPath",
                "label": "Records JSON Path",
                "type": "text",
                "required": False,
                "placeholder": "data.accounts",
                "helpText": "Dot-separated path to the account array. Leave empty when the response itself is an array.",
            },
            {
                "name": "timeoutSeconds",
                "label": "Timeout (seconds)",
                "type": "number",
                "required": True,
                "default": 30,
            },
            {
                "name": "verifySsl",
                "label": "Verify SSL Certificate",
                "type": "boolean",
                "required": False,
                "default": True,
            },
        ]
    }

    def validate_configuration(self) -> None:
        endpoint = str(self.configuration.get("endpointUrl") or "").strip()
        if not endpoint:
            raise ConnectorConfigurationError("endpointUrl is required.")
        if not endpoint.lower().startswith(("http://", "https://")):
            raise ConnectorConfigurationError("endpointUrl must start with http:// or https://.")

        method = str(self.configuration.get("method", "GET")).upper()
        if method not in {"GET", "POST"}:
            raise ConnectorConfigurationError("Only GET and POST are supported.")

        auth_type = str(self.configuration.get("authType", "NONE")).upper()
        if auth_type not in {"NONE", "BEARER", "BASIC", "API_KEY"}:
            raise ConnectorConfigurationError("Unsupported authentication type.")
        if auth_type == "BEARER" and not self.configuration.get("bearerToken"):
            raise ConnectorConfigurationError("Bearer token is required.")
        if auth_type == "BASIC" and not self.configuration.get("username"):
            raise ConnectorConfigurationError("Username is required for basic authentication.")
        if auth_type == "API_KEY" and not self.configuration.get("apiKeyValue"):
            raise ConnectorConfigurationError("API key value is required.")

        self._parse_json_object("headersJson", default={})
        if self.configuration.get("requestBodyJson"):
            self._parse_json_object("requestBodyJson", default={})

    def _parse_json_object(self, key: str, default: dict[str, Any]) -> dict[str, Any]:
        raw = self.configuration.get(key)
        if raw in (None, ""):
            return default
        if isinstance(raw, dict):
            return raw
        try:
            value = json.loads(str(raw))
        except json.JSONDecodeError as exc:
            raise ConnectorConfigurationError(f"{key} must contain valid JSON.") from exc
        if not isinstance(value, dict):
            raise ConnectorConfigurationError(f"{key} must contain a JSON object.")
        return value

    def _build_request(self) -> Request:
        endpoint = str(self.configuration["endpointUrl"]).strip()
        method = str(self.configuration.get("method", "GET")).upper()
        headers = {"Accept": "application/json"}
        headers.update(
            {str(k): str(v) for k, v in self._parse_json_object("headersJson", {}).items()}
        )

        auth_type = str(self.configuration.get("authType", "NONE")).upper()
        if auth_type == "BEARER":
            headers["Authorization"] = f"Bearer {self.configuration.get('bearerToken', '')}"
        elif auth_type == "BASIC":
            credentials = f"{self.configuration.get('username', '')}:{self.configuration.get('password', '')}"
            encoded = b64encode(credentials.encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {encoded}"
        elif auth_type == "API_KEY":
            header_name = str(self.configuration.get("apiKeyHeader") or "X-API-Key")
            headers[header_name] = str(self.configuration.get("apiKeyValue") or "")

        body: bytes | None = None
        if method == "POST":
            payload = self._parse_json_object("requestBodyJson", {})
            body = json.dumps(payload).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        return Request(endpoint, data=body, headers=headers, method=method)

    def _request_json(self) -> Any:
        self.validate_configuration()
        timeout = max(1, int(self.configuration.get("timeoutSeconds", 30)))
        verify_ssl = bool(self.configuration.get("verifySsl", True))
        context = None if verify_ssl else ssl._create_unverified_context()

        try:
            with urlopen(self._build_request(), timeout=timeout, context=context) as response:
                status_code = int(getattr(response, "status", 200))
                content_type = str(response.headers.get("Content-Type", ""))
                body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ConnectorError(f"Web service returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise ConnectorError(f"Unable to connect to web service: {exc.reason}") from exc

        if status_code < 200 or status_code >= 300:
            raise ConnectorError(f"Web service returned HTTP {status_code}.")

        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConnectorError(
                f"Web service response is not valid JSON (Content-Type: {content_type or 'unknown'})."
            ) from exc

    def _extract_records(self, payload: Any) -> list[dict[str, Any]]:
        current = payload
        records_path = str(self.configuration.get("recordsPath") or "").strip()
        if records_path:
            for segment in records_path.split("."):
                if not isinstance(current, dict) or segment not in current:
                    raise ConnectorError(f"Records path '{records_path}' was not found in the response.")
                current = current[segment]

        if not isinstance(current, list):
            raise ConnectorError(
                "The configured records path must resolve to a JSON array of account objects."
            )
        if not current:
            return []
        if not all(isinstance(item, dict) for item in current):
            raise ConnectorError("Account array must contain JSON objects.")
        return current

    @staticmethod
    def _flatten_record(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        for key, value in record.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                flattened.update(WebServiceConnector._flatten_record(value, name))
            elif isinstance(value, list):
                flattened[name] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            elif value is None:
                flattened[name] = ""
            else:
                flattened[name] = value
        return flattened

    def _records_to_csv(self, records: list[dict[str, Any]]) -> bytes:
        flattened = [self._flatten_record(record) for record in records]
        headers: list[str] = []
        seen: set[str] = set()
        for record in flattened:
            for key in record:
                if key not in seen:
                    seen.add(key)
                    headers.append(key)

        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for record in flattened:
            writer.writerow(record)
        return output.getvalue().encode("utf-8-sig")

    def test_connection(self) -> ConnectionTestResult:
        payload = self._request_json()
        records = self._extract_records(payload)
        return ConnectionTestResult(
            success=True,
            message="Web service connection succeeded and returned a valid account array.",
            details={
                "recordCount": len(records),
                "recordsPath": str(self.configuration.get("recordsPath") or ""),
            },
        )

    def fetch_file(self) -> ConnectorFile:
        payload = self._request_json()
        records = self._extract_records(payload)
        content = self._records_to_csv(records)
        return ConnectorFile(
            content=content,
            filename="web_service_accounts.csv",
            source_path=str(self.configuration.get("endpointUrl") or ""),
            size=len(content),
            modified_at=datetime.utcnow(),
            metadata={
                "connectorType": "WEB_SERVICE",
                "recordCount": len(records),
                "responseFormat": "JSON",
                "convertedTo": "CSV",
            },
        )
