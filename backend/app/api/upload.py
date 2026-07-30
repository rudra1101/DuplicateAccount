from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.upload_service import read_accounts
from app.services.duplicate_detector import detect_duplicate_groups
from app.store.memory_store import save_scan

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


@router.post("/")
async def upload(file: UploadFile = File(...)):
    try:
        # Read uploaded accounts
        accounts = read_accounts(file.file)

        if not accounts:
            raise HTTPException(
                status_code=400,
                detail="No accounts found in uploaded file."
            )

        # Run AI duplicate detection
        duplicate_groups, duplicate_details = detect_duplicate_groups(accounts)

        # Save results in memory
        save_scan(
            uploaded_accounts=accounts,
            groups=duplicate_groups,
            details=duplicate_details,
        )

        # Calculate statistics
        total_groups = sum(
            len(groups)
            for groups in duplicate_groups.values()
        )

        total_duplicates = sum(
            group["duplicates"]
            for groups in duplicate_groups.values()
            for group in groups
        )

        return {
            "status": "SUCCESS",
            "accountsUploaded": len(accounts),
            "applications": len(duplicate_groups),
            "duplicateGroups": total_groups,
            "duplicateAccounts": total_duplicates,
            "message": "Duplicate detection completed successfully."
        }

    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )