from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.duplicate_finding import DuplicateFindingRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.source_account import SourceAccountRecord
from app.services.account_dormancy_service import (
    dormancy_config_for_application,
    dormancy_mappings,
    inactive_days,
    is_dormant,
)
from app.services.email_service import send_email
from app.services.service_desk_service import (
    create_dormant_account_ticket,
    sync_dormant_account_ticket,
)
from app.services.source_account_inventory_service import (
    list_source_accounts,
    source_account_to_dict,
)


router = APIRouter(prefix="/integrations", tags=["Source Accounts"])


class DormancyActionRequest(BaseModel):
    requestedBy: str | None = None


def _account_or_404(
    db: Session,
    *,
    integration_id: int,
    account_id: int,
) -> SourceAccountRecord:
    account = db.scalar(
        select(SourceAccountRecord).where(
            SourceAccountRecord.id == account_id,
            SourceAccountRecord.integration_id == integration_id,
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Source account not found.")
    return account


def _dormancy_context(
    db: Session,
    *,
    integration_id: int,
    account: SourceAccountRecord,
):
    integration = db.get(IntegrationRecord, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    config = dormancy_config_for_application(
        integration.configuration,
        account.application,
    )
    if config is None:
        raise HTTPException(
            status_code=400,
            detail="Dormant account detection is not configured for this application.",
        )
    if not is_dormant(account, config):
        raise HTTPException(
            status_code=409,
            detail="The account is no longer dormant under the current application threshold.",
        )
    days = inactive_days(account.last_login_at)
    if days is None:
        raise HTTPException(status_code=409, detail="The account has no normalized last-login timestamp.")
    return integration, config, days


@router.get("/{integration_id}/accounts")
def get_source_accounts(
    integration_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200, alias="pageSize"),
    search: str = Query(default=""),
    active: bool | None = Query(default=None),
    account_state: str | None = Query(default=None, alias="accountState"),
    dormant: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    integration = db.get(IntegrationRecord, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    try:
        rows, total = list_source_accounts(
            db,
            integration_id=integration_id,
            page=page,
            page_size=page_size,
            search=search,
            active=active,
            account_state=account_state,
            dormant=dormant,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    configs = dormancy_mappings(integration.configuration)
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "items": [
            source_account_to_dict(
                item,
                configs.get(item.application.strip().casefold()),
            )
            for item in rows
        ],
    }


@router.get("/{integration_id}/accounts/{account_id}")
def get_source_account(
    integration_id: int,
    account_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    account = _account_or_404(
        db,
        integration_id=integration_id,
        account_id=account_id,
    )
    integration = db.get(IntegrationRecord, integration_id)
    config = dormancy_config_for_application(
        integration.configuration if integration is not None else None,
        account.application,
    )
    return source_account_to_dict(account, config)


@router.post("/{integration_id}/accounts/{account_id}/dormancy-reminder")
def send_dormancy_reminder(
    integration_id: int,
    account_id: int,
    payload: DormancyActionRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    account = _account_or_404(db, integration_id=integration_id, account_id=account_id)
    _integration, config, days = _dormancy_context(
        db,
        integration_id=integration_id,
        account=account,
    )
    if not account.email:
        raise HTTPException(
            status_code=400,
            detail="The dormant account does not have an email address.",
        )

    account_name = account.display_name or account.username or account.native_identity
    subject = f"Action required: inactive {account.application} account"
    text_body = (
        f"Hello {account_name},\n\n"
        f"Your {account.application} account has not recorded a login for {days} days. "
        f"The configured inactivity threshold is {config.threshold_days} days.\n\n"
        "If you still require this account, please sign in or contact the support team. "
        "The account may otherwise be disabled according to the organization's access policy.\n\n"
        "This is an automated IdentityAI account-governance reminder."
    )
    safe_account_name = escape(account_name)
    safe_application = escape(account.application)
    html_body = (
        f"<p>Hello {safe_account_name},</p>"
        f"<p>Your <strong>{safe_application}</strong> account has not recorded a login "
        f"for <strong>{days} days</strong>. The configured inactivity threshold is "
        f"<strong>{config.threshold_days} days</strong>.</p>"
        "<p>If you still require this account, please sign in or contact the support team. "
        "The account may otherwise be disabled according to the organization's access policy.</p>"
        "<p>This is an automated IdentityAI account-governance reminder.</p>"
    )

    try:
        send_email(
            recipients=[account.email],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    account.last_dormancy_reminder_at = datetime.now(UTC)
    account.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(account)
    return {
        "accountId": account.id,
        "recipient": account.email,
        "sentAt": account.last_dormancy_reminder_at.isoformat(),
        "inactiveDays": days,
        "thresholdDays": config.threshold_days,
        "requestedBy": (payload.requestedBy or "").strip() or None,
    }


@router.post("/{integration_id}/accounts/{account_id}/dormancy-disable-ticket")
def create_dormancy_disable_ticket(
    integration_id: int,
    account_id: int,
    payload: DormancyActionRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    account = _account_or_404(db, integration_id=integration_id, account_id=account_id)
    _integration, config, days = _dormancy_context(
        db,
        integration_id=integration_id,
        account=account,
    )
    try:
        return create_dormant_account_ticket(
            db,
            account=account,
            inactive_days=days,
            threshold_days=config.threshold_days,
            requested_by=payload.requestedBy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{integration_id}/accounts/{account_id}/dormancy-disable-ticket/sync")
def sync_dormancy_disable_ticket(
    integration_id: int,
    account_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("remediation.manage")),
):
    account = _account_or_404(db, integration_id=integration_id, account_id=account_id)
    try:
        return sync_dormant_account_ticket(db, account=account)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{integration_id}/duplicate-findings")
def get_duplicate_findings(
    integration_id: int,
    include_resolved: bool = Query(default=False, alias="includeResolved"),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("duplicate.view")),
):
    if db.get(IntegrationRecord, integration_id) is None:
        raise HTTPException(status_code=404, detail="Integration not found.")

    statement = (
        select(DuplicateFindingRecord)
        .options(
            selectinload(DuplicateFindingRecord.primary_account),
            selectinload(DuplicateFindingRecord.duplicate_account),
        )
        .where(DuplicateFindingRecord.integration_id == integration_id)
        .order_by(DuplicateFindingRecord.confidence.desc(), DuplicateFindingRecord.id.asc())
    )
    if not include_resolved:
        statement = statement.where(DuplicateFindingRecord.active.is_(True))

    findings = list(db.scalars(statement).all())
    return [
        {
            "id": finding.id,
            "integrationId": finding.integration_id,
            "primaryAccount": source_account_to_dict(finding.primary_account),
            "duplicateAccount": source_account_to_dict(finding.duplicate_account),
            "confidence": finding.confidence,
            "status": finding.status,
            "active": finding.active,
            "evidence": finding.evidence or {},
            "firstDetectedAt": finding.first_detected_at.isoformat() if finding.first_detected_at else None,
            "lastDetectedAt": finding.last_detected_at.isoformat() if finding.last_detected_at else None,
            "lastScanId": finding.last_scan_id,
        }
        for finding in findings
    ]
