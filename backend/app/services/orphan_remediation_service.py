from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.orphan_state import OrphanStateRecord
from app.db_models.source_account import SourceAccountRecord
from app.services.service_desk_service import (
    VALID_ACTIONS,
    _config_from_db,
    _field,
    _headers_auth,
    _replace_template_values,
    _utc_now,
)


def _account_key(account: SourceAccountRecord) -> str:
    return str(
        account.native_identity
        or account.username
        or account.email
        or account.employee_id
        or account.id
    )


def _account_label(account: SourceAccountRecord) -> str:
    return str(
        account.display_name
        or account.username
        or account.native_identity
        or account.employee_id
        or account.id
    )


def _render_payload(
    *,
    config,
    orphan: OrphanStateRecord,
    account: SourceAccountRecord,
    action: str,
) -> dict[str, Any]:
    evidence = dict(orphan.evidence or {})
    label = _account_label(account)
    reason = str(evidence.get("reason") or "Persisted orphan correlation did not resolve the account.")
    account_key = _account_key(account)

    variables = {
        "summary": f"IdentityAI orphan remediation - {action.title()} {label}",
        "description": (
            f"IdentityAI identified {label} as a current {orphan.orphan_type} orphan in "
            f"{account.application}. Requested action: {action}. Target account: {account_key}. "
            f"Persisted correlation reason: {reason}"
        ),
        "action": action,
        "account_key": account_key,
        "application": account.application,
        "integration_id": str(orphan.integration_id),
        "username": str(account.username or ""),
        "email": str(account.email or ""),
    }
    payload = json.loads(config.payload_template)
    payload = _replace_template_values(payload, variables)
    if not isinstance(payload, dict):
        raise ValueError("Rendered ticket payload must be a JSON object.")
    return payload


def serialize_orphan_ticket(
    orphan: OrphanStateRecord,
    account: SourceAccountRecord,
) -> dict[str, Any]:
    return {
        "resultType": "orphan_remediation_ticket",
        "created": bool(orphan.service_desk_ticket_id),
        "orphanStateId": orphan.id,
        "sourceAccountId": orphan.source_account_id,
        "integrationId": orphan.integration_id,
        "application": account.application,
        "displayName": account.display_name,
        "username": account.username,
        "email": account.email,
        "employeeId": account.employee_id,
        "nativeIdentity": account.native_identity,
        "orphanType": orphan.orphan_type,
        "orphanStatus": orphan.status,
        "remediationAction": orphan.remediation_action,
        "ticketId": orphan.service_desk_ticket_id,
        "ticketStatus": orphan.service_desk_ticket_status,
        "ticketUrl": orphan.service_desk_ticket_url,
        "ticketCreatedAt": orphan.ticket_created_at.isoformat() if orphan.ticket_created_at else None,
        "ticketLastSyncedAt": orphan.ticket_last_synced_at.isoformat() if orphan.ticket_last_synced_at else None,
        "ticketError": orphan.ticket_error,
    }


def create_orphan_ticket(
    db: Session,
    *,
    source_account_id: int,
    action: str,
    requested_by: str | None = None,
) -> dict[str, Any]:
    config = _config_from_db(db)
    if not config.enabled:
        raise ValueError("Service Desk integration is disabled.")

    normalized_action = str(action or "").strip().upper()
    if normalized_action not in VALID_ACTIONS:
        raise ValueError("Remediation action must be DISABLE or DELETE.")

    orphan = db.scalar(
        select(OrphanStateRecord).where(
            OrphanStateRecord.source_account_id == int(source_account_id),
            OrphanStateRecord.active.is_(True),
        )
    )
    if orphan is None:
        raise ValueError("Current orphan state not found for that source account.")
    if orphan.service_desk_ticket_id:
        raise ValueError("A Service Desk ticket already exists for this orphan account.")

    account = db.get(SourceAccountRecord, int(source_account_id))
    if account is None:
        raise ValueError("Source account not found.")

    payload = _render_payload(
        config=config,
        orphan=orphan,
        account=account,
        action=normalized_action,
    )
    headers, auth = _headers_auth(config)
    url = urljoin(config.base_url + "/", config.create_path.lstrip("/"))

    try:
        with httpx.Client(timeout=20, verify=config.verify_tls) as client:
            response = client.post(url, json=payload, headers=headers, auth=auth)
            response.raise_for_status()
            data = response.json()

        ticket_id = _field(data, config.ticket_id_field)
        if ticket_id is None:
            raise RuntimeError(
                "Ticket response did not contain configured ticket ID field "
                f"'{config.ticket_id_field}'."
            )
    except Exception as exc:
        orphan.remediation_action = normalized_action
        orphan.actioned_by = (requested_by or "").strip() or None
        orphan.ticket_error = str(exc)
        orphan.ticket_last_synced_at = _utc_now()
        orphan.updated_at = _utc_now()
        db.commit()
        raise RuntimeError(f"Service Desk ticket creation failed: {exc}") from exc

    ticket_status = _field(data, config.ticket_status_field)
    ticket_url = _field(data, config.ticket_url_field)
    now = _utc_now()
    orphan.remediation_action = normalized_action
    orphan.actioned_by = (requested_by or "").strip() or None
    orphan.service_desk_ticket_id = str(ticket_id)
    orphan.service_desk_ticket_status = (
        str(ticket_status) if ticket_status is not None else "CREATED"
    )
    orphan.service_desk_ticket_url = str(ticket_url) if ticket_url else None
    orphan.ticket_created_at = now
    orphan.ticket_last_synced_at = now
    orphan.ticket_error = None
    orphan.updated_at = now
    db.commit()
    db.refresh(orphan)

    return serialize_orphan_ticket(orphan, account)
