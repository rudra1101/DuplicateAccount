\
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.chat import ChatHistoryMessage, ChatRequest

def live_tests_enabled() -> bool:
    return os.getenv("RUN_RUDRIX_LIVE_TESTS", "").strip().lower() in {
        "1", "true", "yes", "on",
    }

@pytest.fixture
def chat_request_factory():
    def _build(
        message: str,
        *,
        history: list[tuple[str, str]] | None = None,
        conversation_id: str | None = None,
        reasoning: bool = False,
    ) -> ChatRequest:
        return ChatRequest(
            message=message,
            conversationId=conversation_id,
            history=[
                ChatHistoryMessage(role=role, content=content)
                for role, content in (history or [])
            ],
            useReasoningModel=reasoning,
        )
    return _build

@pytest.fixture
def require_live_rudrix():
    if not live_tests_enabled():
        pytest.skip(
            "Set RUN_RUDRIX_LIVE_TESTS=1 to run tests against Ollama "
            "and the local IdentityAI database."
        )

@pytest.fixture
def db_session(require_live_rudrix):
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
