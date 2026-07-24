from pydantic import BaseModel
from app.schemas.account import DuplicateResult


class UploadResponse(BaseModel):
    accounts_uploaded: int
    duplicates_found: int
    duplicates: list[DuplicateResult]