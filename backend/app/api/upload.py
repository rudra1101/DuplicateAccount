from fastapi import APIRouter, UploadFile, File

from app.services.upload_service import read_accounts
from app.ai.duplicate_engine import detect_duplicates
from app.schemas.upload import UploadResponse
from app.services.review_service import scan_accounts

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

@router.post("/", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):

    accounts = read_accounts(file.file)

    duplicates = scan_accounts(accounts)

    return UploadResponse(
        accounts_uploaded=len(accounts),
        duplicates_found=len(duplicates),
        duplicates=duplicates
    )