from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.ai.agent_service import (
    run_identity_agent,
)
from app.database.session import (
    get_db,
)
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)


router = APIRouter(
    prefix="/chat",
    tags=["AI Assistant"],
)


@router.post(
    "/",
    response_model=ChatResponse,
)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    try:
        return run_identity_agent(
            db=db,
            request=payload,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "AI assistant request failed: "
                f"{exc}"
            ),
        ) from exc