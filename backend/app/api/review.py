from fastapi import APIRouter

from app.services.review_service import (
    get_review_summary,
    get_duplicate_groups,
    get_duplicate_group_details,
)

router = APIRouter(
    prefix="/review",
    tags=["Review Queue"],
)


@router.get("/")
def review_summary():
    return get_review_summary()


@router.get("/{application}")
def application_groups(application: str):
    return get_duplicate_groups(application)


@router.get("/details/{group_id}")
def duplicate_group(group_id: int):
    return get_duplicate_group_details(group_id)