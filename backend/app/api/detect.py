from fastapi import APIRouter

from app.services.account_loader import load_accounts
from app.services.duplicate_detector import detect_duplicate_groups


router = APIRouter(
    prefix="/detect",
    tags=["Duplicate Detection"],
)


@router.get("/")
def detect():
    accounts = load_accounts()

    duplicate_groups, duplicate_details = detect_duplicate_groups(accounts)

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
        "accountsScanned": len(accounts),
        "duplicateGroupsFound": total_groups,
        "duplicateAccountsFound": total_duplicate_accounts,
        "groups": dict(duplicate_groups),
        "details": duplicate_details,
    }