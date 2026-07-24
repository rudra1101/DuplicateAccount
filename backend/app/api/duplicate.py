from fastapi import APIRouter

from app.schemas.account import Account
from app.ai.duplicate_engine import detect_duplicates

router = APIRouter(prefix="/duplicates", tags=["Duplicate Detection"])


@router.post("/scan")
def scan(accounts: list[Account]):
    return detect_duplicates(accounts)