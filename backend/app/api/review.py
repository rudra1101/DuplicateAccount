from fastapi import APIRouter

router = APIRouter(
    prefix="/review",
    tags=["Review Queue"]
)

@router.get("/")
def review_queue():
    return [
        {
            "id": 1,
            "application": "Active Directory",
            "account1": "john.smith",
            "account2": "jsmith",
            "confidence": 96,
        },
        {
            "id": 2,
            "application": "Entra ID",
            "account1": "rudra.shankar",
            "account2": "rudra.s",
            "confidence": 91,
        },
    ]