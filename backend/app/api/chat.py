from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.agent_service import run_identity_agent
from app.auth import get_current_user
from app.database.session import get_db
from app.db_models.chat_conversation import ChatConversationRecord
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_history_service import (
    get_or_create_conversation,
    save_chat_message,
)
from app.services.chat_ownership_service import assign_new_conversation_owner


router = APIRouter(
    prefix="/chat",
    tags=["AI Assistant"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        if payload.conversationId:
            existing = db.get(ChatConversationRecord, payload.conversationId)
            if existing is not None and existing.user_id != user.id:
                raise HTTPException(status_code=404, detail="Conversation not found.")

        conversation_id = payload.conversationId or str(uuid.uuid4())

        conversation = get_or_create_conversation(
            db=db,
            conversation_id=conversation_id,
            first_message=payload.message,
        )
        if conversation is not None:
            assign_new_conversation_owner(
                db,
                conversation=conversation,
                user_id=user.id,
            )

        save_chat_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=payload.message,
        )

        agent_request = payload.model_copy(
            update={"conversationId": conversation_id}
        )
        response = run_identity_agent(db=db, request=agent_request)

        save_chat_message(
            db=db,
            conversation_id=conversation_id,
            role="assistant",
            content=response.message,
            model=response.model,
            sources=[source.model_dump() for source in response.sources],
        )

        db.commit()
        return response

    except HTTPException:
        db.rollback()
        raise
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="AI assistant request failed.") from exc
