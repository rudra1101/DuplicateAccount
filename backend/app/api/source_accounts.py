from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.duplicate_finding import DuplicateFindingRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.source_account import SourceAccountRecord
from app.services.source_account_inventory_service import (
    list_source_accounts,
    source_account_to_dict,
)


router = APIRouter(prefix="/integrations", tags=["Source Accounts"])


@router.get("/{integration_id}/accounts")
def get_source_accounts(
    integration_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200, alias="pageSize"),
    search: str = Query(default=""),
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    if db.get(IntegrationRecord, integration_id) is None:
        raise HTTPException(status_code=404, detail="Integration not found.")
    rows, total = list_source_accounts(
        db,
        integration_id=integration_id,
        page=page,
        page_size=page_size,
        search=search,
        active=active,
    )
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "items": [source_account_to_dict(item) for item in rows],
    }


@router.get("/{integration_id}/accounts/{account_id}")
def get_source_account(
    integration_id: int,
    account_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    account = db.scalar(
        select(SourceAccountRecord).where(
            SourceAccountRecord.id == account_id,
            SourceAccountRecord.integration_id == integration_id,
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Source account not found.")
    return source_account_to_dict(account)


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
