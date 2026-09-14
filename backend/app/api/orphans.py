from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.account import AccountRecord
from app.db_models.identity import IdentityRecord
from app.db_models.orphan_finding import OrphanFindingRecord
from app.db_models.scan import ScanRecord
from app.services.correlation_policy_service import get_policy_for_account_integration
from app.services.orphan_detection_service import detect_orphan_findings

router = APIRouter(prefix="/orphans", tags=["Orphan Accounts"])


def _finding_to_dict(finding: OrphanFindingRecord, account: AccountRecord) -> dict:
    return {
        "id": finding.id,
        "findingType": finding.finding_type,
        "orphanType": finding.orphan_type,
        "scanId": finding.scan_id,
        "accountId": finding.account_id,
        "application": account.application,
        "username": account.username,
        "displayName": account.display_name,
        "email": account.email,
        "employeeId": account.employee_id,
        "accountStatus": account.status,
        "correlationMethod": finding.correlation_method,
        "matchedIdentityId": finding.matched_identity_id,
        "evidence": finding.evidence or {},
        "status": finding.status,
        "createdAt": finding.created_at.isoformat(),
    }


def _latest_scan_id_for_integration(db: Session, integration_id: int) -> int | None:
    return db.scalar(
        select(ScanRecord.id)
        .where(ScanRecord.integration_id == integration_id, ScanRecord.status == "COMPLETED")
        .order_by(ScanRecord.created_at.desc(), ScanRecord.id.desc())
        .limit(1)
    )


@router.post("/scans/{scan_id}/detect")
def detect_for_scan(scan_id: int, db: Session = Depends(get_db), _user=Depends(require_permission("duplicate.view"))):
    scan = db.get(ScanRecord, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.integration_id is None:
        raise HTTPException(status_code=400, detail="Scan is not linked to an integration.")
    policy = get_policy_for_account_integration(db, scan.integration_id)
    if policy is None:
        raise HTTPException(status_code=400, detail="No enabled correlation policy is configured for this account integration.")
    identity_count = db.scalar(
        select(func.count(IdentityRecord.id)).where(IdentityRecord.integration_id == policy.authoritative_integration_id)
    ) or 0
    if identity_count == 0:
        raise HTTPException(status_code=400, detail="The selected authoritative source has no identities loaded. Run it first.")
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
    _user=Depends(require_permission("duplicate.view")),
):
    effective_scan_id = scan_id
    if effective_scan_id is None and integration_id is not None and latest_only:
        effective_scan_id = _latest_scan_id_for_integration(db, integration_id)
        if effective_scan_id is None:
            return []
    statement = select(OrphanFindingRecord, AccountRecord).join(
        AccountRecord, AccountRecord.id == OrphanFindingRecord.account_id
    ).join(ScanRecord, ScanRecord.id == OrphanFindingRecord.scan_id)
    if effective_scan_id is not None:
        statement = statement.where(OrphanFindingRecord.scan_id == effective_scan_id)
    elif integration_id is not None:
        statement = statement.where(ScanRecord.integration_id == integration_id)
    if orphan_type:
        statement = statement.where(OrphanFindingRecord.orphan_type == orphan_type.strip().upper())
    statement = statement.order_by(
        OrphanFindingRecord.orphan_type.asc(),
        OrphanFindingRecord.created_at.desc(),
    )
    return [_finding_to_dict(finding, account) for finding, account in db.execute(statement).all()]


@router.get("/summary")
def summary(
    scan_id: int | None = Query(default=None, alias="scanId"),
    integration_id: int | None = Query(default=None, alias="integrationId"),
    latest_only: bool = Query(default=True, alias="latestOnly"),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("duplicate.view")),
):
    effective_scan_id = scan_id
    if effective_scan_id is None and integration_id is not None and latest_only:
        effective_scan_id = _latest_scan_id_for_integration(db, integration_id)
        if effective_scan_id is None:
            return {"total": 0, "byType": {}}
    total_stmt = select(func.count(OrphanFindingRecord.id))
    type_stmt = select(OrphanFindingRecord.orphan_type, func.count(OrphanFindingRecord.id)).group_by(OrphanFindingRecord.orphan_type)
    if effective_scan_id is not None:
        total_stmt = total_stmt.where(OrphanFindingRecord.scan_id == effective_scan_id)
        type_stmt = type_stmt.where(OrphanFindingRecord.scan_id == effective_scan_id)
    elif integration_id is not None:
        total_stmt = total_stmt.join(ScanRecord, ScanRecord.id == OrphanFindingRecord.scan_id).where(ScanRecord.integration_id == integration_id)
        type_stmt = type_stmt.join(ScanRecord, ScanRecord.id == OrphanFindingRecord.scan_id).where(ScanRecord.integration_id == integration_id)
    return {
        "total": int(db.scalar(total_stmt) or 0),
        "byType": {kind: int(count) for kind, count in db.execute(type_stmt)},
    }
