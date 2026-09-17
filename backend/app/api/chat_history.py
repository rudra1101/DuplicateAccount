from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.agent_service import run_identity_agent
from app.auth import get_current_user
from app.database.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_history_service import (
    generate_ai_conversation_title,
    get_conversation_details,
    get_regeneration_context,
    rename_conversation,
    replace_last_assistant_response,
    serialize_conversation_summary,
)
from app.services.chat_ownership_service import (
    clear_owned_conversations,
    ensure_owned_conversation,
    list_owned_conversations,
)


router = APIRouter(
    prefix="/chat-history",
    tags=["Chat History"],
    dependencies=[Depends(get_current_user)],
)


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=60)


class RegenerateConversationRequest(BaseModel):
    useReasoningModel: bool = False


def _owned_or_404(db: Session, conversation_id: str, user_id: int):
    try:
        return ensure_owned_conversation(
            db,
            conversation_id=conversation_id,
            user_id=user_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc


@router.get("/")
def get_chat_history(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return [
        serialize_conversation_summary(conversation)
        for conversation in list_owned_conversations(
            db,
            user_id=user.id,
            limit=limit,
        )
    ]


@router.get("/{conversation_id}")
def get_chat_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _owned_or_404(db, conversation_id, user.id)
    conversation = get_conversation_details(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.post("/{conversation_id}/generate-title")
def generate_chat_title(
    conversation_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        _owned_or_404(db, conversation_id, user.id)
        result = generate_ai_conversation_title(db, conversation_id=conversation_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the conversation title.",
        ) from exc


@router.post("/{conversation_id}/regenerate", response_model=ChatResponse)
def regenerate_last_response(
    conversation_id: str,
    payload: RegenerateConversationRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        _owned_or_404(db, conversation_id, user.id)
        context = get_regeneration_context(db, conversation_id=conversation_id)
        if context is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation or user message was not found.",
            )

        request = ChatRequest(
            message=context["message"],
            conversationId=conversation_id,
            history=context["history"],
            useReasoningModel=payload.useReasoningModel,
        )
        response = run_identity_agent(db=db, request=request)
        replace_last_assistant_response(
            db,
            conversation_id=conversation_id,
            assistant_message_ids=context["assistantMessageIds"],
            content=response.message,
            model=response.model,
            sources=[source.model_dump() for source in response.sources],
        )
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to regenerate the response.") from exc


@router.patch("/{conversation_id}")
def update_chat_conversation_title(
    conversation_id: str,
    payload: RenameConversationRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        _owned_or_404(db, conversation_id, user.id)
        result = rename_conversation(
            db,
            conversation_id=conversation_id,
            title=payload.title,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to rename the conversation.") from exc


@router.delete("/{conversation_id}")
def remove_chat_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        conversation = _owned_or_404(db, conversation_id, user.id)
        db.delete(conversation)
        db.commit()
        return {"deleted": True, "conversationId": conversation_id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to delete the conversation.") from exc


@router.delete("/")
def remove_all_chat_conversations(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        deleted_count = clear_owned_conversations(db, user_id=user.id)
        db.commit()
        return {"deleted": True, "deletedCount": deleted_count}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to clear chat history.") from exc
