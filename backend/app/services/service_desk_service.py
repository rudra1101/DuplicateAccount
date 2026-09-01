from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.db_models.remediation_item import RemediationItemRecord
from app.db_models.review_decision_history import ReviewDecisionHistoryRecord
from app.services.settings_service import decrypt_secret, get_application_settings


VALID_AUTH_TYPES = {"NONE", "BEARER", "BASIC"}
VALID_ACTIONS = {"DISABLE", "DELETE"}


@dataclass(frozen=True)
class ServiceDeskConfig:
    enabled: bool
    name: str
    base_url: str
    auth_type: str
    username: str
    secret: str
    create_path: str
    status_path: str
    ticket_id_field: str
    ticket_status_field: str
    ticket_url_field: str
    completed_statuses: set[str]
    payload_template: str
    verify_tls: bool


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _field(data: Any, path: str) -> Any:
    current = data
    for part in [item for item in path.split(".") if item]:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _config_from_db(db: Session) -> ServiceDeskConfig:
    settings = get_application_settings(db)
    if settings is None:
        raise ValueError("Service Desk is not configured.")
    return ServiceDeskConfig(
        enabled=settings.service_desk_enabled,
        name=settings.service_desk_name.strip() or "Service Desk",
        base_url=settings.service_desk_base_url.rstrip("/"),
        auth_type=settings.service_desk_auth_type.strip().upper(),
        username=settings.service_desk_username.strip(),
        secret=decrypt_secret(settings.service_desk_secret_encrypted),
        create_path=settings.service_desk_create_path,
        status_path=settings.service_desk_status_path,
        ticket_id_field=settings.service_desk_ticket_id_field,
        ticket_status_field=settings.service_desk_ticket_status_field,
        ticket_url_field=settings.service_desk_ticket_url_field,
        completed_statuses={item.strip().lower() for item in settings.service_desk_completed_statuses.split(",") if item.strip()},
        payload_template=settings.service_desk_payload_template,
        verify_tls=settings.service_desk_verify_tls,
    )


def service_desk_settings_response(db: Session) -> dict[str, Any]:
    settings = get_application_settings(db)
    if settings is None:
        return {
            "enabled": False, "name": "Service Desk", "baseUrl": "", "authType": "BEARER",
            "username": "", "secretConfigured": False, "createPath": "/tickets",
            "statusPath": "/tickets/{ticket_id}", "ticketIdField": "id",
            "ticketStatusField": "status", "ticketUrlField": "url",
            "completedStatuses": ["completed", "resolved", "closed"],
            "payloadTemplate": '{"summary":"{{summary}}","description":"{{description}}","action":"{{action}}","accountKey":"{{account_key}}","application":"{{application}}"}',
            "verifyTls": True,
        }
    return {
        "enabled": settings.service_desk_enabled,
        "name": settings.service_desk_name,
        "baseUrl": settings.service_desk_base_url,
        "authType": settings.service_desk_auth_type,
        "username": settings.service_desk_username,
        "secretConfigured": bool(settings.service_desk_secret_encrypted),
        "createPath": settings.service_desk_create_path,
        "statusPath": settings.service_desk_status_path,
        "ticketIdField": settings.service_desk_ticket_id_field,
        "ticketStatusField": settings.service_desk_ticket_status_field,
        "ticketUrlField": settings.service_desk_ticket_url_field,
        "completedStatuses": [item.strip() for item in settings.service_desk_completed_statuses.split(",") if item.strip()],
        "payloadTemplate": settings.service_desk_payload_template,
        "verifyTls": settings.service_desk_verify_tls,
    }


def _headers_auth(config: ServiceDeskConfig) -> tuple[dict[str, str], httpx.BasicAuth | None]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    auth = None
    if config.auth_type == "BEARER" and config.secret:
        headers["Authorization"] = f"Bearer {config.secret}"
    elif config.auth_type == "BASIC":
        auth = httpx.BasicAuth(config.username, config.secret)
    return headers, auth


def update_service_desk_settings(db: Session, **values: Any) -> None:
    from app.services.settings_service import encrypt_secret, get_or_create_application_settings

    auth_type = str(values["auth_type"]).strip().upper()
    if auth_type not in VALID_AUTH_TYPES:
        raise ValueError("Auth type must be NONE, BEARER, or BASIC.")
    base_url = str(values["base_url"]).strip().rstrip("/")
    if values["enabled"] and not base_url:
        raise ValueError("Base URL is required when Service Desk is enabled.")
    if values["enabled"] and not str(values["create_path"]).strip():
        raise ValueError("Create ticket path is required.")
    if values["enabled"] and "{ticket_id}" not in str(values["status_path"]):
        raise ValueError("Status path must contain {ticket_id}.")
    try:
        parsed = json.loads(str(values["payload_template"]))
        if not isinstance(parsed, dict):
            raise ValueError
    except Exception as exc:
        raise ValueError("Ticket payload template must be a valid JSON object.") from exc

    settings = get_or_create_application_settings(db)
    settings.service_desk_enabled = bool(values["enabled"])
    settings.service_desk_name = str(values["name"]).strip() or "Service Desk"
    settings.service_desk_base_url = base_url
    settings.service_desk_auth_type = auth_type
    settings.service_desk_username = str(values["username"]).strip()
    settings.service_desk_create_path = str(values["create_path"]).strip()
    settings.service_desk_status_path = str(values["status_path"]).strip()
    settings.service_desk_ticket_id_field = str(values["ticket_id_field"]).strip() or "id"
    settings.service_desk_ticket_status_field = str(values["ticket_status_field"]).strip() or "status"
    settings.service_desk_ticket_url_field = str(values["ticket_url_field"]).strip() or "url"
    settings.service_desk_completed_statuses = ",".join(sorted({str(item).strip().lower() for item in values["completed_statuses"] if str(item).strip()}))
    settings.service_desk_payload_template = str(values["payload_template"])
    settings.service_desk_verify_tls = bool(values["verify_tls"])
    if values.get("clear_secret"):
        settings.service_desk_secret_encrypted = None
    elif values.get("secret"):
        settings.service_desk_secret_encrypted = encrypt_secret(str(values["secret"]))
    db.commit()


def _render_payload(config: ServiceDeskConfig, item: RemediationItemRecord, target_data: dict[str, Any], action: str) -> dict[str, Any]:
    account_name = str(target_data.get("username") or target_data.get("email") or item.target_account_key or "account")
    variables = {
        "summary": f"IdentityAI duplicate remediation - {action.title()} {account_name}",
        "description": f"IdentityAI confirmed a duplicate account pair in {item.application}. Requested action: {action}. Target account: {account_name}. Confidence: {item.confidence if item.confidence is not None else 'N/A'}.",
        "action": action,
        "account_key": item.target_account_key or "",
        "application": item.application,
        "integration_id": str(item.integration_id),
        "username": str(target_data.get("username") or ""),
        "email": str(target_data.get("email") or ""),
    }
    rendered = config.payload_template
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", value.replace('"', '\\"'))
    payload = json.loads(rendered)
    if not isinstance(payload, dict):
        raise ValueError("Rendered ticket payload must be a JSON object.")
    return payload


def create_ticket(db: Session, *, item_id: int, target: str, action: str, requested_by: str | None = None) -> dict[str, Any]:
    config = _config_from_db(db)
    if not config.enabled:
        raise ValueError("Service Desk integration is disabled.")
    action = action.strip().upper()
    if action not in VALID_ACTIONS:
        raise ValueError("Remediation action must be DISABLE or DELETE.")
    item = db.get(RemediationItemRecord, item_id)
    if item is None:
        raise ValueError("Remediation item not found.")
    if item.service_desk_ticket_id:
        raise ValueError("A Service Desk ticket already exists for this remediation item.")
    if target not in {"ACCOUNT_1", "ACCOUNT_2"}:
        raise ValueError("Target must be ACCOUNT_1 or ACCOUNT_2.")

    item.target_account_key = item.account_1_key if target == "ACCOUNT_1" else item.account_2_key
    target_data = item.account_1_data if target == "ACCOUNT_1" else item.account_2_data
    item.remediation_action = action
    payload = _render_payload(config, item, target_data or {}, action)
    headers, auth = _headers_auth(config)
    url = urljoin(config.base_url + "/", config.create_path.lstrip("/"))

    try:
        with httpx.Client(timeout=20, verify=config.verify_tls) as client:
            response = client.post(url, json=payload, headers=headers, auth=auth)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        item.ticket_error = str(exc)
        item.status = "FAILED"
        item.updated_at = _utc_now()
        db.commit()
        raise RuntimeError(f"Service Desk ticket creation failed: {exc}") from exc

    ticket_id = _field(data, config.ticket_id_field)
    if ticket_id is None:
        raise RuntimeError(f"Ticket response did not contain configured ticket ID field '{config.ticket_id_field}'.")
    ticket_status = _field(data, config.ticket_status_field)
    ticket_url = _field(data, config.ticket_url_field)
    now = _utc_now()
    item.service_desk_ticket_id = str(ticket_id)
    item.service_desk_ticket_status = str(ticket_status) if ticket_status is not None else "CREATED"
    item.service_desk_ticket_url = str(ticket_url) if ticket_url else None
    item.ticket_created_at = now
    item.ticket_last_synced_at = now
    item.ticket_error = None
    item.status = "TICKET_OPEN"
    item.actioned_by = (requested_by or "").strip() or None
    item.action_comment = f"{action.title()} requested through {config.name} ticket {ticket_id}."
    item.updated_at = now
    db.commit()
    db.refresh(item)
    return serialize_ticket(item)


def serialize_ticket(item: RemediationItemRecord) -> dict[str, Any]:
    return {
        "id": item.id,
        "status": item.status,
        "remediationAction": item.remediation_action,
        "targetAccountKey": item.target_account_key,
        "ticketId": item.service_desk_ticket_id,
        "ticketStatus": item.service_desk_ticket_status,
        "ticketUrl": item.service_desk_ticket_url,
        "ticketCreatedAt": item.ticket_created_at.isoformat() if item.ticket_created_at else None,
        "ticketLastSyncedAt": item.ticket_last_synced_at.isoformat() if item.ticket_last_synced_at else None,
        "ticketError": item.ticket_error,
    }


def sync_ticket(db: Session, item: RemediationItemRecord) -> dict[str, Any]:
    if not item.service_desk_ticket_id:
        raise ValueError("Remediation item has no Service Desk ticket.")
    config = _config_from_db(db)
    headers, auth = _headers_auth(config)
    path = config.status_path.replace("{ticket_id}", item.service_desk_ticket_id)
    url = urljoin(config.base_url + "/", path.lstrip("/"))
    try:
        with httpx.Client(timeout=20, verify=config.verify_tls) as client:
            response = client.get(url, headers=headers, auth=auth)
            response.raise_for_status()
            data = response.json()
        status_value = _field(data, config.ticket_status_field)
        if status_value is None:
            raise RuntimeError(f"Ticket response did not contain configured status field '{config.ticket_status_field}'.")
        item.service_desk_ticket_status = str(status_value)
        ticket_url = _field(data, config.ticket_url_field)
        if ticket_url:
            item.service_desk_ticket_url = str(ticket_url)
        item.ticket_last_synced_at = _utc_now()
        item.ticket_error = None

        if str(status_value).strip().lower() in config.completed_statuses and item.status != "ACTIONED":
            item.status = "ACTIONED"
            item.action_comment = f"Service Desk ticket {item.service_desk_ticket_id} completed. {item.remediation_action or 'Remediation'} marked completed."
            db.add(
                ReviewDecisionHistoryRecord(
                    integration_id=item.integration_id,
                    application=item.application,
                    account_1_key=item.account_1_key,
                    account_2_key=item.account_2_key,
                    decision="REMEDIATED",
                    confidence=item.confidence,
                    reviewer_name=item.actioned_by,
                    comment=item.action_comment,
                    source="SERVICE_DESK",
                    account_1_data=item.account_1_data or {},
                    account_2_data=item.account_2_data or {},
                )
            )
        item.updated_at = _utc_now()
        db.commit()
        db.refresh(item)
        return serialize_ticket(item)
    except Exception as exc:
        item.ticket_last_synced_at = _utc_now()
        item.ticket_error = str(exc)
        db.commit()
        raise RuntimeError(f"Service Desk ticket sync failed: {exc}") from exc


def sync_ticket_by_id(db: Session, item_id: int) -> dict[str, Any]:
    item = db.get(RemediationItemRecord, item_id)
    if item is None:
        raise ValueError("Remediation item not found.")
    return sync_ticket(db, item)


def sync_open_tickets() -> None:
    with SessionLocal() as db:
        settings = get_application_settings(db)
        if settings is None or not settings.service_desk_enabled:
            return
        items = list(db.scalars(select(RemediationItemRecord).where(RemediationItemRecord.status == "TICKET_OPEN", RemediationItemRecord.service_desk_ticket_id.is_not(None))).all())
        for item in items:
            try:
                sync_ticket(db, item)
            except Exception:
                continue
