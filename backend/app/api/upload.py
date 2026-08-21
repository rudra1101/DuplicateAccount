from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.services.account_loader import load_uploaded_accounts
from app.services.duplicate_detector import detect_duplicate_groups
from app.services.scan_repository import save_completed_scan
from app.store import memory_store


router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


@router.post("/")
async def upload_accounts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("upload.manage")),
):
    filename = file.filename or "uploaded_accounts.csv"

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
        )

    try:
        # Manual uploads are intentionally not tied to a configured
        # integration. The persisted ScanRecord therefore uses
        # integration_id=None, while integration-triggered scans continue
        # to store the originating integration id.
        accounts = load_uploaded_accounts(file.file)

        (
            duplicate_groups,
            duplicate_details,
        ) = detect_duplicate_groups(accounts)

        memory_store.accounts = accounts
        memory_store.duplicate_groups = duplicate_groups
        memory_store.duplicate_details = duplicate_details
        memory_store.last_scan = datetime.now()

        save_completed_scan(
            db=db,
            integration_id=None,
            filename=filename,
            accounts=accounts,
            duplicate_groups=duplicate_groups,
            duplicate_details=duplicate_details,
        )

        total_groups = sum(
            len(groups)
            for groups in duplicate_groups.values()
        )

        total_duplicate_accounts = sum(
            int(group.get("duplicates", 0) or 0)
            for groups in duplicate_groups.values()
            for group in groups
        )

        return {
            "message": "Upload successful",
            "accounts": len(accounts),
            "applications": len(
                {
                    str(account.application).strip()
                    for account in accounts
                    if str(account.application).strip()
                }
            ),
            "duplicateGroups": total_groups,
            "duplicateAccounts": total_duplicate_accounts,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
