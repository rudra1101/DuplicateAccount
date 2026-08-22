from fastapi import APIRouter

from app.models.account import Account
from app.services.duplicate_detector import detect_duplicate_groups
from app.services.review_candidate_service import detect_review_candidates


router = APIRouter(
    prefix="/duplicates",
    tags=["Duplicate Detection"],
)


@router.post("/scan")
def scan(accounts: list[Account]):
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


@router.post("/review-candidates")
def review_candidates(accounts: list[Account]):
    candidates = detect_review_candidates(accounts)
    return {
        "accountsScanned": len(accounts),
        "reviewCandidatesFound": len(candidates),
        "candidates": candidates,
    }
