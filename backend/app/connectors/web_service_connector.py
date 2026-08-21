from __future__ import annotations

import csv
import io
import json
import ssl
from base64 import b64encode
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.connectors.base import BaseFileConnector, ConnectionTestResult, ConnectorFile
from app.connectors.exceptions import ConnectorConfigurationError, ConnectorError
from app.connectors.registry import ConnectorRegistry


@ConnectorRegistry.register("WEB_SERVICE")
class WebServiceConnector(BaseFileConnector):
    display_name = "Web Service (REST API)"

    description = (
        "Read account data from REST APIs with Basic, API token, OAuth 2.0, "
        "Bearer, or custom-header authentication."
    )

    configuration_schema = {
        "fields": [
            {
                "name": "endpointUrl",
                "label": "Account Endpoint URL",
                "type": "text",
                "required": True,
                "placeholder": "https://api.example.com/v1/accounts",
                "helpText": "REST endpoint used to retrieve account records.",
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
                "label": "Authentication Type",
                "type": "select",
                "required": True,
                "default": "NONE",
                "options": [
                    {"label": "No Authentication", "value": "NONE"},
                    {"label": "Basic Authentication", "value": "BASIC"},
                    {"label": "API Token", "value": "API_TOKEN"},
                    {"label": "Bearer Token", "value": "BEARER"},
                    {"label": "OAuth 2.0", "value": "OAUTH2"},
                    {"label": "Custom Header Authentication", "value": "CUSTOM_HEADER"},
                ],
            },
            {
                "name": "username",
                "label": "Username",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["BASIC"]},
            },
            {
                "name": "password",
                "label": "Password",
                "type": "password",
                "required": False,
                "visibleWhen": {"authType": ["BASIC"]},
            },
            {
                "name": "apiToken",
                "label": "API Token",
                "type": "password",
                "required": False,
                "visibleWhen": {"authType": ["API_TOKEN"]},
                "helpText": "Token value. Bearer is used by default unless a token prefix is supplied.",
            },
            {
                "name": "apiTokenHeader",
                "label": "API Token Header",
                "type": "text",
                "required": False,
                "default": "Authorization",
                "visibleWhen": {"authType": ["API_TOKEN"]},
            },
            {
                "name": "bearerToken",
                "label": "Bearer Token",
                "type": "password",
                "required": False,
                "visibleWhen": {"authType": ["BEARER"]},
            },
            {
                "name": "oauthGrantType",
                "label": "OAuth 2.0 Grant Type",
                "type": "select",
                "required": False,
                "default": "CLIENT_CREDENTIALS",
                "visibleWhen": {"authType": ["OAUTH2"]},
                "options": [
                    {"label": "Client Credentials", "value": "CLIENT_CREDENTIALS"},
                    {"label": "Password", "value": "PASSWORD"},
                    {"label": "Refresh Token", "value": "REFRESH_TOKEN"},
                    {"label": "JWT Bearer Token", "value": "JWT_BEARER"},
                    {"label": "SAML Bearer Assertion", "value": "SAML_BEARER"},
                ],
            },
            {
                "name": "tokenUrl",
                "label": "Token URL",
                "type": "text",
                "required": False,
                "placeholder": "https://login.example.com/oauth2/token",
                "visibleWhen": {"authType": ["OAUTH2"]},
            },
            {
                "name": "clientId",
                "label": "Client ID",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"]},
            },
            {
                "name": "clientSecret",
                "label": "Client Secret",
                "type": "password",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"]},
            },
            {
                "name": "oauthUsername",
                "label": "OAuth Username",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"], "oauthGrantType": ["PASSWORD"]},
            },
            {
                "name": "oauthPassword",
                "label": "OAuth Password",
                "type": "password",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"], "oauthGrantType": ["PASSWORD"]},
            },
            {
                "name": "refreshToken",
                "label": "Refresh Token",
                "type": "password",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"], "oauthGrantType": ["REFRESH_TOKEN"]},
            },
            {
                "name": "oauthAssertion",
                "label": "JWT / SAML Assertion",
                "type": "password",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"], "oauthGrantType": ["JWT_BEARER", "SAML_BEARER"]},
                "helpText": "Signed assertion supplied by the target application's authentication setup.",
            },
            {
                "name": "oauthScope",
                "label": "OAuth Scope",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"]},
                "placeholder": "accounts.read",
            },
            {
                "name": "oauthHeadersJson",
                "label": "OAuth Token Headers (JSON)",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"]},
                "placeholder": "{\"Accept\":\"application/json\"}",
            },
            {
                "name": "oauthParametersJson",
                "label": "Additional OAuth Parameters (JSON)",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"]},
                "placeholder": "{\"resource\":\"https://api.example.com\"}",
            },
            {
                "name": "customAuthHeader",
                "label": "Custom Authentication Header",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["CUSTOM_HEADER"]},
                "placeholder": "X-Custom-Auth",
            },
            {
                "name": "customAuthValue",
                "label": "Custom Authentication Value",
                "type": "password",
                "required": False,
                "visibleWhen": {"authType": ["CUSTOM_HEADER"]},
            },
            {
                "name": "headersJson",
                "label": "Additional Request Headers (JSON)",
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
            },
            {
                "name": "recordsPath",
                "label": "Records JSON Path",
                "type": "text",
                "required": False,
                "placeholder": "data.accounts",
                "helpText": "Dot-separated path to the account array. Leave empty for a root JSON array.",
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
        allowed = {"NONE", "BASIC", "API_TOKEN", "BEARER", "OAUTH2", "CUSTOM_HEADER"}
        if auth_type not in allowed:
            raise ConnectorConfigurationError("Unsupported authentication type.")

        if auth_type == "BASIC":
            if not self.configuration.get("username") or not self.configuration.get("password"):
                raise ConnectorConfigurationError("Username and password are required for Basic Authentication.")
        elif auth_type == "API_TOKEN":
            if not self.configuration.get("apiToken"):
                raise ConnectorConfigurationError("API token is required.")
        elif auth_type == "BEARER":
            if not self.configuration.get("bearerToken"):
                raise ConnectorConfigurationError("Bearer token is required.")
        elif auth_type == "CUSTOM_HEADER":
            if not self.configuration.get("customAuthHeader") or not self.configuration.get("customAuthValue"):
                raise ConnectorConfigurationError("Custom authentication header and value are required.")
        elif auth_type == "OAUTH2":
            self._validate_oauth()

        self._parse_json_object("headersJson", default={})
        self._parse_json_object("oauthHeadersJson", default={})
        self._parse_json_object("oauthParametersJson", default={})
        if self.configuration.get("requestBodyJson"):
            self._parse_json_object("requestBodyJson", default={})

    def _validate_oauth(self) -> None:
        token_url = str(self.configuration.get("tokenUrl") or "").strip()
        if not token_url:
            raise ConnectorConfigurationError("Token URL is required for OAuth 2.0.")

        grant = str(self.configuration.get("oauthGrantType", "CLIENT_CREDENTIALS")).upper()
        if grant not in {"CLIENT_CREDENTIALS", "PASSWORD", "REFRESH_TOKEN", "JWT_BEARER", "SAML_BEARER"}:
            raise ConnectorConfigurationError("Unsupported OAuth 2.0 grant type.")

        if grant in {"CLIENT_CREDENTIALS", "PASSWORD", "REFRESH_TOKEN"}:
            if not self.configuration.get("clientId") or not self.configuration.get("clientSecret"):
                raise ConnectorConfigurationError("Client ID and Client Secret are required for this OAuth grant.")
        if grant == "PASSWORD" and (
            not self.configuration.get("oauthUsername") or not self.configuration.get("oauthPassword")
        ):
            raise ConnectorConfigurationError("OAuth username and password are required for Password grant.")
        if grant == "REFRESH_TOKEN" and not self.configuration.get("refreshToken"):
            raise ConnectorConfigurationError("Refresh token is required for Refresh Token grant.")
        if grant in {"JWT_BEARER", "SAML_BEARER"} and not self.configuration.get("oauthAssertion"):
            raise ConnectorConfigurationError("A signed JWT/SAML assertion is required for this grant.")

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

    def _ssl_context(self):
        return None if bool(self.configuration.get("verifySsl", True)) else ssl._create_unverified_context()

    def _oauth_access_token(self) -> str:
        token_url = str(self.configuration.get("tokenUrl") or "").strip()
        grant = str(self.configuration.get("oauthGrantType", "CLIENT_CREDENTIALS")).upper()
        params: dict[str, Any] = self._parse_json_object("oauthParametersJson", {})

        if grant == "CLIENT_CREDENTIALS":
            params.setdefault("grant_type", "client_credentials")
        elif grant == "PASSWORD":
            params.setdefault("grant_type", "password")
            params.setdefault("username", str(self.configuration.get("oauthUsername") or ""))
            params.setdefault("password", str(self.configuration.get("oauthPassword") or ""))
        elif grant == "REFRESH_TOKEN":
            params.setdefault("grant_type", "refresh_token")
            params.setdefault("refresh_token", str(self.configuration.get("refreshToken") or ""))
        elif grant == "JWT_BEARER":
            params.setdefault("grant_type", "urn:ietf:params:oauth:grant-type:jwt-bearer")
            params.setdefault("assertion", str(self.configuration.get("oauthAssertion") or ""))
        elif grant == "SAML_BEARER":
            params.setdefault("grant_type", "urn:ietf:params:oauth:grant-type:saml2-bearer")
            params.setdefault("assertion", str(self.configuration.get("oauthAssertion") or ""))

        client_id = str(self.configuration.get("clientId") or "")
        client_secret = str(self.configuration.get("clientSecret") or "")
        if client_id:
            params.setdefault("client_id", client_id)
        if client_secret:
            params.setdefault("client_secret", client_secret)

        scope = str(self.configuration.get("oauthScope") or "").strip()
        if scope:
            params.setdefault("scope", scope)

        headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
        headers.update({str(k): str(v) for k, v in self._parse_json_object("oauthHeadersJson", {}).items()})
        request = Request(token_url, data=urlencode(params).encode("utf-8"), headers=headers, method="POST")
        timeout = max(1, int(self.configuration.get("timeoutSeconds", 30)))

        try:
            with urlopen(request, timeout=timeout, context=self._ssl_context()) as response:
                body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ConnectorError(f"OAuth token endpoint returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise ConnectorError(f"Unable to connect to OAuth token endpoint: {exc.reason}") from exc

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConnectorError("OAuth token endpoint did not return valid JSON.") from exc

        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not token:
            raise ConnectorError("OAuth token response does not contain access_token.")
        return str(token)

    def _build_request(self) -> Request:
        endpoint = str(self.configuration["endpointUrl"]).strip()
        method = str(self.configuration.get("method", "GET")).upper()
        headers = {"Accept": "application/json"}
        headers.update({str(k): str(v) for k, v in self._parse_json_object("headersJson", {}).items()})

        auth_type = str(self.configuration.get("authType", "NONE")).upper()
        if auth_type == "BEARER":
            headers["Authorization"] = f"Bearer {self.configuration.get('bearerToken', '')}"
        elif auth_type == "BASIC":
            credentials = f"{self.configuration.get('username', '')}:{self.configuration.get('password', '')}"
            encoded = b64encode(credentials.encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {encoded}"
        elif auth_type == "API_TOKEN":
            header_name = str(self.configuration.get("apiTokenHeader") or "Authorization")
            token = str(self.configuration.get("apiToken") or "")
            if header_name.lower() == "authorization" and " " not in token:
                token = f"Bearer {token}"
            headers[header_name] = token
        elif auth_type == "OAUTH2":
            headers["Authorization"] = f"Bearer {self._oauth_access_token()}"
        elif auth_type == "CUSTOM_HEADER":
            headers[str(self.configuration.get("customAuthHeader") or "X-Custom-Auth")] = str(
                self.configuration.get("customAuthValue") or ""
            )

        body: bytes | None = None
        if method == "POST":
            payload = self._parse_json_object("requestBodyJson", {})
            body = json.dumps(payload).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        return Request(endpoint, data=body, headers=headers, method=method)

    def _request_json(self) -> Any:
        self.validate_configuration()
        timeout = max(1, int(self.configuration.get("timeoutSeconds", 30)))

        try:
            with urlopen(self._build_request(), timeout=timeout, context=self._ssl_context()) as response:
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
            raise ConnectorError("The configured records path must resolve to a JSON array of account objects.")
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
                "authenticationType": str(self.configuration.get("authType", "NONE")).upper(),
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
