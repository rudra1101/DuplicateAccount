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
from app.schemas.review import (
    CandidateDecisionRequest,
)
from app.services.review_service import (
    get_duplicate_group_details,
    get_duplicate_groups,
    get_review_summary,
    get_scan_status,
    save_candidate_decision,
)


router = APIRouter(
    prefix="/review",
    tags=["Review Queue"],
)


@router.get("/")
def review_summary(
    integration_id: int | None = Query(
        default=None,
        alias="integrationId",
        ge=1,
        description=(
            "Return review data for the latest "
            "completed scan of this integration. "
            "When omitted, return review data for "
            "all integrations."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Return the review-queue summary.

    Examples:

    GET /api/review/
    GET /api/review/?integrationId=1
    """

    try:
        return get_review_summary(
            db=db,
            integration_id=integration_id,
        )

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load review summary "
                "from the database."
            ),
        ) from exc


@router.get("/status")
def review_scan_status(
    integration_id: int | None = Query(
        default=None,
        alias="integrationId",
        ge=1,
        description=(
            "Return scan status for a specific "
            "integration. When omitted, return "
            "the overall review scan status."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Return scan status.

    Examples:

    GET /api/review/status
    GET /api/review/status?integrationId=1
    """

    try:
        return get_scan_status(
            db=db,
            integration_id=integration_id,
        )

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load review scan status."
            ),
        ) from exc


@router.get("/details/{group_id}")
def duplicate_group_details(
    group_id: int,
    integration_id: int | None = Query(
        default=None,
        alias="integrationId",
        ge=1,
        description=(
            "Optional integration ID used to "
            "verify that the duplicate group "
            "belongs to the selected integration."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Return primary-account and duplicate-candidate
    details for one database duplicate-group ID.

    Examples:

    GET /api/review/details/25
    GET /api/review/details/25?integrationId=1
    """

    try:
        result = get_duplicate_group_details(
            db=db,
            group_id=group_id,
            integration_id=integration_id,
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Duplicate group was not found "
                    "for the selected integration "
                    "and its latest completed scan."
                ),
            )

        return result

    except HTTPException:
        raise

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load duplicate-group "
                "details from the database."
            ),
        ) from exc


@router.post(
    "/candidates/{candidate_id}/decision",
)
def submit_candidate_decision(
    candidate_id: int,
    payload: CandidateDecisionRequest,
    db: Session = Depends(get_db),
):
    """
    Save a reviewer decision for a duplicate candidate.

    The candidate ID must be candidateRecordId from the
    duplicate-group details response.
    """

    try:
        return save_candidate_decision(
            db=db,
            candidate_id=candidate_id,
            decision=payload.decision,
            comment=payload.comment,
            reviewer_name=(
                payload.reviewerName
            ),
        )

    except ValueError as exc:
        message = str(exc)

        status_code = (
            404
            if "not found" in message.lower()
            else 400
        )

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save candidate "
                "decision in the database."
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save candidate "
                f"decision: {exc}"
            ),
        ) from exc


@router.get("/{application}")
def application_groups(
    application: str,
    integration_id: int | None = Query(
        default=None,
        alias="integrationId",
        ge=1,
        description=(
            "Integration whose latest completed "
            "scan should be used."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Return duplicate groups for an application.

    Examples:

    GET /api/review/ADP%20HR?integrationId=1
    GET /api/review/Active%20Directory?integrationId=2
    """

    try:
        return get_duplicate_groups(
            db=db,
            application=application,
            integration_id=integration_id,
        )

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load duplicate groups "
                "for the selected application "
                "and integration."
            ),
        ) from exc