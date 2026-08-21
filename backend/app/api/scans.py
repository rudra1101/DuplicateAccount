from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.account import AccountRecord
from app.db_models.scan import ScanRecord


router = APIRouter(
    prefix="/scans",
    tags=["Scans"],
)


@router.get("/")
def get_scans(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("duplicate.view")),
):
    statement = (
        select(ScanRecord)
        .order_by(desc(ScanRecord.created_at))
    )

    scans = db.scalars(statement).all()

    return [
        {
            "id": scan.id,
            "filename": scan.filename,
            "status": scan.status,
            "accountsScanned": scan.accounts_scanned,
            "applicationCount": scan.application_count,
            "duplicateGroupCount": scan.duplicate_group_count,
            "duplicateAccountCount": scan.duplicate_account_count,
            "highConfidenceCount": scan.high_confidence_count,
            "createdAt": scan.created_at.isoformat(),
        }
        for scan in scans
    ]


@router.get("/{scan_id}/accounts")
def get_scan_accounts(
    scan_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100, alias="pageSize"),
    search: str = Query(default=""),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    scan = db.get(ScanRecord, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    filters = [AccountRecord.scan_id == scan_id]
    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        filters.append(
            or_(
                AccountRecord.username.ilike(pattern),
                AccountRecord.display_name.ilike(pattern),
                AccountRecord.email.ilike(pattern),
                AccountRecord.employee_id.ilike(pattern),
                AccountRecord.source_account_id.ilike(pattern),
                AccountRecord.application.ilike(pattern),
            )
        )

    total = db.scalar(
        select(func.count(AccountRecord.id)).where(*filters)
    ) or 0

    statement = (
        select(AccountRecord)
        .where(*filters)
        .order_by(AccountRecord.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    accounts = db.scalars(statement).all()

    return {
        "scanId": scan.id,
        "filename": scan.filename,
        "page": page,
        "pageSize": page_size,
        "total": int(total),
        "items": [
            {
                "id": account.id,
                "sourceAccountId": account.source_account_id,
                "application": account.application,
                "username": account.username,
                "displayName": account.display_name,
                "email": account.email,
                "employeeId": account.employee_id,
                "department": account.department,
                "manager": account.manager,
                "status": account.status,
                "created": account.created,
                "rawAttributes": account.raw_attributes or {},
            }
            for account in accounts
        ],
    }


@router.get("/{scan_id}")
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("duplicate.view")),
):
    scan = db.get(
        ScanRecord,
        scan_id,
    )

    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    return {
        "id": scan.id,
        "filename": scan.filename,
        "status": scan.status,
        "accountsScanned": scan.accounts_scanned,
        "applicationCount": scan.application_count,
        "duplicateGroupCount": scan.duplicate_group_count,
        "duplicateAccountCount": scan.duplicate_account_count,
        "highConfidenceCount": scan.high_confidence_count,
        "createdAt": scan.created_at.isoformat(),
    }
