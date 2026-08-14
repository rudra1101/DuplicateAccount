from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.chat_history_service import (
    clear_conversations,
    delete_conversation,
    get_conversation_details,
    list_conversations,
    rename_conversation,
)


router = APIRouter(
    prefix="/chat-history",
    tags=["Chat History"],
)


class RenameConversationRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=60,
    )


@router.get("/")
def get_chat_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    return list_conversations(
        db,
        limit=limit,
    )


@router.get("/{conversation_id}")
def get_chat_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    conversation = get_conversation_details(
        db,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return conversation


@router.patch("/{conversation_id}")
def update_chat_conversation_title(
    conversation_id: str,
    payload: RenameConversationRequest,
    db: Session = Depends(get_db),
):
    try:
        result = rename_conversation(
            db,
            conversation_id=conversation_id,
            title=payload.title,
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        db.commit()

        return result

    except HTTPException:
        db.rollback()
        raise

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to rename the conversation."
            ),
        ) from exc


@router.delete("/{conversation_id}")
def remove_chat_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    try:
        deleted = delete_conversation(
            db,
            conversation_id=conversation_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        db.commit()

        return {
            "deleted": True,
            "conversationId": conversation_id,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to delete the conversation."
            ),
        ) from exc


@router.delete("/")
def remove_all_chat_conversations(
    db: Session = Depends(get_db),
):
    try:
        deleted_count = clear_conversations(
            db
        )

        db.commit()

        return {
            "deleted": True,
            "deletedCount": deleted_count,
        }

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to clear chat history.",
        ) from exc