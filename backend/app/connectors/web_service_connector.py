from __future__ import annotations

import csv
import io
import json
from base64 import b64encode
from datetime import datetime
from typing import Any

import httpx

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
                "visibleWhen": {"authType": ["OAUTH2"]},
                "placeholder": "https://login.example.com/oauth2/token",
            },
            {
                "name": "clientId",
                "label": "Client ID",
                "type": "text",
                "required": False,
                "visibleWhen": {
                    "authType": ["OAUTH2"],
                    "oauthGrantType": ["CLIENT_CREDENTIALS", "PASSWORD", "REFRESH_TOKEN"],
                },
            },
            {
                "name": "clientSecret",
                "label": "Client Secret",
                "type": "password",
                "required": False,
                "visibleWhen": {
                    "authType": ["OAUTH2"],
                    "oauthGrantType": ["CLIENT_CREDENTIALS", "PASSWORD", "REFRESH_TOKEN"],
                },
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
                "name": "oauthAdvanced",
                "label": "Show advanced OAuth options",
                "type": "boolean",
                "required": False,
                "default": False,
                "visibleWhen": {"authType": ["OAUTH2"]},
            },
            {
                "name": "oauthHeadersJson",
                "label": "OAuth Token Headers (JSON)",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"], "oauthAdvanced": [True]},
                "placeholder": "{\"X-Custom-Header\":\"value\"}",
                "helpText": "Optional custom token headers. Accept and Content-Type are added automatically.",
            },
            {
                "name": "oauthParametersJson",
                "label": "Additional OAuth Parameters (JSON)",
                "type": "text",
                "required": False,
                "visibleWhen": {"authType": ["OAUTH2"], "oauthAdvanced": [True]},
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
        if auth_type not in {"NONE", "BASIC", "API_TOKEN", "BEARER", "OAUTH2", "CUSTOM_HEADER"}:
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

        self._parse_json_object("headersJson", {})
        self._parse_json_object("oauthHeadersJson", {})
        self._parse_json_object("oauthParametersJson", {})
        if self.configuration.get("requestBodyJson"):
            self._parse_json_object("requestBodyJson", {})

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
            return dict(default)
        if isinstance(raw, dict):
            return dict(raw)
        try:
            value = json.loads(str(raw))
        except json.JSONDecodeError as exc:
            raise ConnectorConfigurationError(f"{key} must contain valid JSON.") from exc
        if not isinstance(value, dict):
            raise ConnectorConfigurationError(f"{key} must contain a JSON object.")
        return value

    def _timeout(self) -> float:
        return float(max(1, int(self.configuration.get("timeoutSeconds", 30))))

    def _verify_ssl(self) -> bool:
        return bool(self.configuration.get("verifySsl", True))

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self._timeout(),
            verify=self._verify_ssl(),
            follow_redirects=True,
            headers={
                "User-Agent": "DuplicateAccount-WebServiceConnector/1.0",
                "Accept": "application/json",
            },
        )

    def _oauth_parameters(self) -> dict[str, Any]:
        grant = str(self.configuration.get("oauthGrantType", "CLIENT_CREDENTIALS")).upper()
        params = self._parse_json_object("oauthParametersJson", {})

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

        if grant in {"CLIENT_CREDENTIALS", "PASSWORD", "REFRESH_TOKEN"}:
            params.setdefault("client_id", str(self.configuration.get("clientId") or ""))
            params.setdefault("client_secret", str(self.configuration.get("clientSecret") or ""))

        scope = str(self.configuration.get("oauthScope") or "").strip()
        if scope:
            params.setdefault("scope", scope)

        return params

    def _oauth_access_token(self) -> tuple[str, dict[str, Any]]:
        self._validate_oauth()
        token_url = str(self.configuration.get("tokenUrl") or "").strip()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        custom_headers = self._parse_json_object("oauthHeadersJson", {})
        for key, value in custom_headers.items():
            if str(key).lower() == "content-type":
                continue
            headers[str(key)] = str(value)

        try:
            with self._client() as client:
                response = client.post(
                    token_url,
                    data=self._oauth_parameters(),
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Unable to connect to OAuth token endpoint: {exc}") from exc

        if response.status_code < 200 or response.status_code >= 300:
            detail = response.text[:700]
            raise ConnectorError(
                f"OAuth token endpoint returned HTTP {response.status_code}: {detail}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ConnectorError("OAuth token endpoint did not return valid JSON.") from exc

        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not token:
            raise ConnectorError("OAuth token response does not contain access_token.")

        safe_details = {
            "statusCode": response.status_code,
            "tokenType": payload.get("token_type") if isinstance(payload, dict) else None,
            "expiresIn": payload.get("expires_in") if isinstance(payload, dict) else None,
            "scope": payload.get("scope") if isinstance(payload, dict) else None,
            "grantType": str(self.configuration.get("oauthGrantType", "CLIENT_CREDENTIALS")).upper(),
        }
        return str(token), safe_details

    def test_authentication(self) -> ConnectionTestResult:
        self.validate_configuration()
        auth_type = str(self.configuration.get("authType", "NONE")).upper()

        if auth_type == "OAUTH2":
            _token, details = self._oauth_access_token()
            return ConnectionTestResult(
                success=True,
                message="OAuth authentication succeeded and an access token was issued.",
                details={"authenticationType": auth_type, **details},
            )

        if auth_type == "NONE":
            return ConnectionTestResult(
                success=True,
                message="No authentication is configured for this connection.",
                details={"authenticationType": auth_type},
            )

        return ConnectionTestResult(
            success=True,
            message=f"{auth_type.replace('_', ' ').title()} authentication configuration is valid.",
            details={"authenticationType": auth_type},
        )

    def _request_headers(self) -> dict[str, str]:
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
            token, _details = self._oauth_access_token()
            headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "CUSTOM_HEADER":
            headers[str(self.configuration.get("customAuthHeader") or "X-Custom-Auth")] = str(
                self.configuration.get("customAuthValue") or ""
            )

        return headers

    def _request_json(self) -> Any:
        self.validate_configuration()
        endpoint = str(self.configuration["endpointUrl"]).strip()
        method = str(self.configuration.get("method", "GET")).upper()
        body = None
        if method == "POST":
            body = self._parse_json_object("requestBodyJson", {})

        try:
            with self._client() as client:
                response = client.request(
                    method,
                    endpoint,
                    headers=self._request_headers(),
                    json=body if method == "POST" else None,
                )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Unable to connect to web service: {exc}") from exc

        if response.status_code < 200 or response.status_code >= 300:
            raise ConnectorError(
                f"Web service returned HTTP {response.status_code}: {response.text[:700]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            content_type = response.headers.get("Content-Type", "unknown")
            raise ConnectorError(
                f"Web service response is not valid JSON (Content-Type: {content_type})."
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
