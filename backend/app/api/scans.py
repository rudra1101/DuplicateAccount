from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.db_models.scan import ScanRecord


router = APIRouter(
    prefix="/scans",
    tags=["Scans"],
)


@router.get("/")
def get_scans(
    db: Session = Depends(get_db),
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


@router.get("/{scan_id}")
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
):
    scan = db.get(
        ScanRecord,
        scan_id,
    )

    if scan is None:
        return {
            "message": "Scan not found"
        }

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