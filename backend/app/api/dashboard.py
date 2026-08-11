from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.dashboard_service import (
    build_dashboard_response,
)


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/")
def dashboard(
    period: str = Query(
        default="daily",
        pattern=(
            "^(daily|weekly|monthly|yearly)$"
        ),
    ),
    db: Session = Depends(get_db),
):
    try:
        return build_dashboard_response(
            db=db,
            period=period,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        print(
            "Database error while "
            "loading dashboard:",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load dashboard "
                "information from the database."
            ),
        ) from exc

    except Exception as exc:
        print(
            "Unexpected error while "
            "loading dashboard:",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred "
                "while loading the dashboard."
            ),
        ) from exc