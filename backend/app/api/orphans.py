from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.account import AccountRecord
from app.db_models.identity import IdentityRecord
from app.db_models.orphan_finding import OrphanFindingRecord
from app.db_models.orphan_state import OrphanStateRecord
from app.db_models.scan import ScanRecord
from app.db_models.source_account import SourceAccountRecord
from app.services.correlation_policy_service import get_policy_for_account_integration
from app.services.orphan_detection_service import detect_orphan_findings

router = APIRouter(prefix="/orphans", tags=["Orphan Accounts"])


def _history_to_dict(finding: OrphanFindingRecord, account: AccountRecord) -> dict:
    return {
        "id": finding.id,
        "findingType": finding.finding_type,
        "orphanType": finding.orphan_type,
        "scanId": finding.scan_id,
        "accountId": finding.account_id,
        "sourceAccountId": None,
        "application": account.application,
        "nativeIdentity": account.source_account_id,
        "username": account.username,
        "displayName": account.display_name,
        "email": account.email,
        "employeeId": account.employee_id,
        "accountStatus": account.status,
        "correlationMethod": finding.correlation_method,
        "matchedIdentityId": finding.matched_identity_id,
        "evidence": finding.evidence or {},
        "status": finding.status,
        "active": True,
        "firstDetectedAt": finding.created_at.isoformat(),
        "lastDetectedAt": finding.created_at.isoformat(),
        "createdAt": finding.created_at.isoformat(),
    }


def _state_to_dict(state: OrphanStateRecord, account: SourceAccountRecord) -> dict:
    return {
        "id": state.id,
        "findingType": "ORPHAN_ACCOUNT",
        "orphanType": state.orphan_type,
        "scanId": state.last_scan_id,
        "accountId": account.id,
        "sourceAccountId": account.id,
        "application": account.application,
        "nativeIdentity": account.native_identity,
        "username": account.username,
        "displayName": account.display_name,
        "email": account.email,
        "employeeId": account.employee_id,
        "accountStatus": account.status,
        "correlationMethod": state.correlation_method,
        "matchedIdentityId": state.matched_identity_id,
        "evidence": state.evidence or {},
        "status": state.status,
        "active": state.active,
        "firstDetectedAt": state.first_detected_at.isoformat(),
        "lastDetectedAt": state.last_detected_at.isoformat(),
        "createdAt": state.first_detected_at.isoformat(),
    }


@router.post("/scans/{scan_id}/detect")
def detect_for_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("duplicate.view")),
):
    scan = db.get(ScanRecord, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.integration_id is None:
        raise HTTPException(status_code=400, detail="Scan is not linked to an integration.")
    policy = get_policy_for_account_integration(db, scan.integration_id)
    if policy is None:
        raise HTTPException(status_code=400, detail="No enabled correlation policy is configured for this account integration.")
    identity_count = db.scalar(
        select(func.count(IdentityRecord.id)).where(
            IdentityRecord.integration_id == policy.authoritative_integration_id,
            IdentityRecord.active.is_(True),
            IdentityRecord.deleted.is_(False),
        )
    ) or 0
    if identity_count == 0:
        raise HTTPException(status_code=400, detail="The selected authoritative source has no active identities loaded. Run it first.")
    try:
        findings = detect_orphan_findings(db, scan_id=scan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "scanId": scan_id,
        "correlationPolicyId": policy.id,
        "correlationPolicyName": policy.name,
        "authoritativeIntegrationId": policy.authoritative_integration_id,
        "authoritativeIdentities": int(identity_count),
        "orphanAccountsFound": len(findings),
    }


@router.get("/")
def list_findings(
    scan_id: int | None = Query(default=None, alias="scanId"),
    integration_id: int | None = Query(default=None, alias="integrationId"),
    latest_only: bool = Query(default=True, alias="latestOnly"),
    orphan_type: str | None = Query(default=None, alias="orphanType"),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    if scan_id is not None:
        statement = select(OrphanFindingRecord, AccountRecord).join(
            AccountRecord, AccountRecord.id == OrphanFindingRecord.account_id
        ).where(OrphanFindingRecord.scan_id == scan_id)
        if orphan_type:
            statement = statement.where(OrphanFindingRecord.orphan_type == orphan_type.strip().upper())
        statement = statement.order_by(OrphanFindingRecord.orphan_type.asc(), OrphanFindingRecord.created_at.desc())
        return [_history_to_dict(finding, account) for finding, account in db.execute(statement).all()]

    if integration_id is None:
        return []

    statement = select(OrphanStateRecord, SourceAccountRecord).join(
        SourceAccountRecord, SourceAccountRecord.id == OrphanStateRecord.source_account_id
    ).where(OrphanStateRecord.integration_id == integration_id)
    if latest_only:
        statement = statement.where(OrphanStateRecord.active.is_(True))
    if orphan_type:
        statement = statement.where(OrphanStateRecord.orphan_type == orphan_type.strip().upper())
    statement = statement.order_by(OrphanStateRecord.orphan_type.asc(), OrphanStateRecord.last_detected_at.desc())
    return [_state_to_dict(state, account) for state, account in db.execute(statement).all()]


@router.get("/summary")
def summary(
    scan_id: int | None = Query(default=None, alias="scanId"),
    integration_id: int | None = Query(default=None, alias="integrationId"),
    latest_only: bool = Query(default=True, alias="latestOnly"),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    if scan_id is not None:
        total_stmt = select(func.count(OrphanFindingRecord.id)).where(OrphanFindingRecord.scan_id == scan_id)
        type_stmt = (
            select(OrphanFindingRecord.orphan_type, func.count(OrphanFindingRecord.id))
            .where(OrphanFindingRecord.scan_id == scan_id)
            .group_by(OrphanFindingRecord.orphan_type)
        )
    elif integration_id is not None:
        filters = [OrphanStateRecord.integration_id == integration_id]
        if latest_only:
            filters.append(OrphanStateRecord.active.is_(True))
        total_stmt = select(func.count(OrphanStateRecord.id)).where(*filters)
        type_stmt = (
            select(OrphanStateRecord.orphan_type, func.count(OrphanStateRecord.id))
            .where(*filters)
            .group_by(OrphanStateRecord.orphan_type)
        )
    else:
        return {"total": 0, "byType": {}}

    return {
        "total": int(db.scalar(total_stmt) or 0),
        "byType": {kind: int(count) for kind, count in db.execute(type_stmt)},
    }
