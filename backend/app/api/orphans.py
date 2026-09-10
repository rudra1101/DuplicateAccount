from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.account import AccountRecord
from app.db_models.identity import IdentityRecord
from app.db_models.orphan_finding import OrphanFindingRecord
from app.db_models.scan import ScanRecord
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
        "confidence": finding.confidence,
        "riskScore": finding.risk_score,
        "severity": finding.severity,
        "correlationMethod": finding.correlation_method,
        "matchedIdentityId": finding.matched_identity_id,
        "evidence": finding.evidence or {},
        "status": finding.status,
        "createdAt": finding.created_at.isoformat(),
    }


@router.post("/scans/{scan_id}/detect")
def detect_for_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("duplicate.view")),
):
    if db.get(ScanRecord, scan_id) is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    identity_count = db.scalar(select(func.count(IdentityRecord.id))) or 0
    if identity_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No authoritative identities are loaded. Run an AUTHORITATIVE integration first.",
        )

    findings = detect_orphan_findings(db, scan_id=scan_id)
    return {
        "scanId": scan_id,
        "authoritativeIdentities": int(identity_count),
        "orphanAccountsFound": len(findings),
    }


@router.get("/")
def list_findings(
    scan_id: int | None = Query(default=None, alias="scanId"),
    severity: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("duplicate.view")),
):
    statement = (
        select(OrphanFindingRecord, AccountRecord)
        .join(AccountRecord, AccountRecord.id == OrphanFindingRecord.account_id)
    )
    if scan_id is not None:
        statement = statement.where(OrphanFindingRecord.scan_id == scan_id)
    if severity:
        statement = statement.where(OrphanFindingRecord.severity == severity.strip().upper())
    statement = statement.order_by(
        OrphanFindingRecord.risk_score.desc(), OrphanFindingRecord.confidence.desc()
    )

    rows = db.execute(statement).all()
    return [_finding_to_dict(finding, account) for finding, account in rows]


@router.get("/summary")
def summary(
    scan_id: int | None = Query(default=None, alias="scanId"),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("duplicate.view")),
):
    filters = []
    if scan_id is not None:
        filters.append(OrphanFindingRecord.scan_id == scan_id)

    total_stmt = select(func.count(OrphanFindingRecord.id))
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = int(db.scalar(total_stmt) or 0)

    severity_stmt = select(
        OrphanFindingRecord.severity,
        func.count(OrphanFindingRecord.id),
    ).group_by(OrphanFindingRecord.severity)
    if filters:
        severity_stmt = severity_stmt.where(*filters)

    return {
        "total": total,
        "bySeverity": {severity: int(count) for severity, count in db.execute(severity_stmt)},
    }
