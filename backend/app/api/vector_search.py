from fastapi import (
    APIRouter,
    HTTPException,
)

from app.ai.vector_store import (
    account_vector_index_service,
    faiss_account_store,
)
from app.schemas.vector_search import (
    VectorAccountSearchRequest,
    VectorTextSearchRequest,
)
from app.services.hybrid_vector_search_service import (
    search_and_rerank_accounts,
)


router = APIRouter(
    prefix="/ai/vector-search",
    tags=["AI Vector Search"],
)


@router.get("/status")
def get_vector_store_status():
    return {
        "available": (
            faiss_account_store.count > 0
        ),
        "vectorCount": (
            faiss_account_store.count
        ),
        "dimension": (
            faiss_account_store.dimension
        ),
    }


@router.post("/text")
def search_by_text(
    payload: VectorTextSearchRequest,
):
    try:
        results = (
            account_vector_index_service
            .search_text(
                payload.query,
                limit=payload.limit,
                minimum_similarity=(
                    payload.minimumSimilarity
                ),
                scan_id=payload.scanId,
            )
        )

        return {
            "query": payload.query,
            "count": len(results),
            "results": [
                result.to_dict()
                for result in results
            ],
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Vector search failed: "
                f"{exc}"
            ),
        ) from exc


@router.post("/account")
def search_by_account(
    payload: VectorAccountSearchRequest,
):
    account = {
        "id": payload.sourceAccountId,
        "application": (
            payload.application
        ),
        "username": payload.username,
        "displayName": (
            payload.displayName
        ),
        "email": payload.email,
        "employeeId": (
            payload.employeeId
        ),
        "department": (
            payload.department
        ),
        "manager": payload.manager,
        "status": payload.status,
        "jobTitle": (
            payload.jobTitle
        ),
        "location": (
            payload.location
        ),
        "phone": payload.phone,
    }

    meaningful_values = [
        value
        for key, value in account.items()
        if (
            key != "id"
            and str(
                value or ""
            ).strip()
        )
    ]

    if not meaningful_values:
        raise HTTPException(
            status_code=400,
            detail=(
                "At least one account attribute "
                "must be provided."
            ),
        )

    try:
        results = (
            search_and_rerank_accounts(
                query_account=account,
                result_limit=payload.limit,
                candidate_limit=(
                    payload.candidateLimit
                ),
                minimum_vector_similarity=(
                    payload.minimumSimilarity
                ),
                minimum_duplicate_confidence=(
                    payload
                    .minimumDuplicateConfidence
                ),
                scan_id=payload.scanId,
                application_filter=(
                    payload.applicationFilter
                ),
                source_account_id=(
                    payload.sourceAccountId
                ),
                exclude_vector_id=(
                    payload.excludeVectorId
                ),
            )
        )

        return {
            "count": len(results),
            "candidateLimit": (
                payload.candidateLimit
            ),
            "minimumVectorSimilarity": (
                payload.minimumSimilarity
            ),
            "minimumDuplicateConfidence": (
                payload
                .minimumDuplicateConfidence
            ),
            "results": [
                result.to_dict()
                for result in results
            ],
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Hybrid account search failed: "
                f"{exc}"
            ),
        ) from exc