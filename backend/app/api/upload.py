from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.services.account_loader import (
    load_uploaded_accounts,
)

from app.services.duplicate_detector import (
    detect_duplicate_groups,
)

from app.services.scan_repository import (
    save_completed_scan,
)

from app.store import memory_store
from app.services.account_loader import load_uploaded_accounts

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


@router.post("/")
async def upload_accounts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
        )

    try:

        ##########################################
        # Read uploaded accounts
        ##########################################

        accounts = load_uploaded_accounts(file.file)

        ##########################################
        # Detect duplicates
        ##########################################

        (
            duplicate_groups,
            duplicate_details,
        ) = detect_duplicate_groups(accounts)

        ##########################################
        # Save in memory
        ##########################################

        memory_store.accounts = accounts

        memory_store.duplicate_groups = duplicate_groups

        memory_store.duplicate_details = duplicate_details

        from datetime import datetime

        memory_store.last_scan = datetime.now()

        ##########################################
        # Save in SQLite
        ##########################################

        save_completed_scan(
            db=db,
            filename=file.filename,
            accounts=accounts,
            duplicate_groups=duplicate_groups,
            duplicate_details=duplicate_details,
        )

        ##########################################
        # Return response
        ##########################################

        total_groups = sum(
            len(groups)
            for groups in duplicate_groups.values()
        )

        total_duplicate_accounts = sum(
            group["duplicates"]
            for groups in duplicate_groups.values()
            for group in groups
        )

        return {
            "message": "Upload successful",
            "accounts": len(accounts),
            "applications": len(
                duplicate_groups
            ),
            "duplicateGroups": total_groups,
            "duplicateAccounts": total_duplicate_accounts,
        }

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex),
        )