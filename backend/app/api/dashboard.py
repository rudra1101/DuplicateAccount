from fastapi import APIRouter

from app.services.dashboard_service import get_dashboard_summary

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/")
def dashboard():
    {
  "accountsScanned": 5231,
  "applications": 4,
  "duplicateGroups": 176,
  "duplicateAccounts": 391,
  "highConfidence": 121,
  "lastScan": "...",
  "trend": [...],
  "sourceDistribution": [...]
}
    return get_dashboard_summary()