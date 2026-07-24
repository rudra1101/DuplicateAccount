import json

from pathlib import Path

from fastapi import APIRouter

from app.services.duplicate_detector import detect_duplicates

router = APIRouter(
    prefix="/detect",
    tags=["Duplicate Detection"]
)


@router.get("/")
def detect():

    file_path = (
        Path(__file__).parent.parent
        / "data"
        / "sample_accounts.json"
    )

    with open(file_path, "r") as file:
        accounts = json.load(file)

    duplicates = detect_duplicates(accounts)

    return {
        "duplicates_found": len(duplicates),
        "results": duplicates,
    }