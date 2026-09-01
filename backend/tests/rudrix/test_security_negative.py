from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.api import chat_feedback as feedback_api
from app.api import chat_history as history_api
from app.api import chat_stream as stream_api
from app.auth import get_current_user
from app.database.session import get_db
from app.schemas.chat import ChatResponse


class FakeDb:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


def build_app(*routers):
    app = FastAPI()
    for router in routers:
        app.include_router(router, prefix="/api")
    return app


def authenticated_user():
    return SimpleNamespace(id=1, username="security-test", role="OWNER")


def test_chat_requires_authentication():
    app = build_app(chat_api.router)
    client = TestClient(app)

    response = client.post(
        "/api/chat/",
        json={"message": "How many duplicate accounts do we have?"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_stream_chat_requires_authentication():
    app = build_app(stream_api.router)
    client = TestClient(app)

    response = client.post(
        "/api/chat/stream",
        json={"message": "How many duplicate accounts do we have?"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_chat_history_requires_authentication():
    app = build_app(history_api.router)
    client = TestClient(app)

    response = client.get("/api/chat-history/")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_chat_feedback_requires_authentication():
    app = build_app(feedback_api.router)
    client = TestClient(app)

    response = client.get("/api/chat-feedback/conversation/test-conversation")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_chat_internal_exception_is_sanitized(monkeypatch):
    fake_db = FakeDb()
    app = build_app(chat_api.router)
    app.dependency_overrides[get_current_user] = authenticated_user
    app.dependency_overrides[get_db] = lambda: fake_db

    monkeypatch.setattr(
        chat_api,
        "get_or_create_conversation",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        chat_api,
        "save_chat_message",
        lambda **kwargs: None,
    )

    secret = "sqlite:///prod.db password=super-secret stacktrace-line-42"

    def explode(*, db, request):
        raise RuntimeError(secret)

    monkeypatch.setattr(chat_api, "run_identity_agent", explode)

    client = TestClient(app)
    response = client.post(
        "/api/chat/",
        json={"message": "Show current duplicate data"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "AI assistant request failed."
    assert secret not in response.text
    assert "super-secret" not in response.text
    assert fake_db.rollbacks == 1


def test_stream_internal_exception_is_sanitized(monkeypatch):
    fake_db = FakeDb()
    app = build_app(stream_api.router)
    app.dependency_overrides[get_current_user] = authenticated_user
    app.dependency_overrides[get_db] = lambda: fake_db

    secret = "postgresql://admin:super-secret@prod/internal stack trace"

    def explode(*, db, request):
        raise RuntimeError(secret)
        yield  # pragma: no cover

    monkeypatch.setattr(stream_api, "run_identity_agent_stream_fast", explode)

    client = TestClient(app)
    response = client.post(
        "/api/chat/stream",
        json={"message": "Show current duplicate data"},
    )

    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[0]["type"] == "start"
    assert events[-1] == {
        "type": "error",
        "message": "AI assistant streaming request failed.",
    }
    assert secret not in response.text
    assert "super-secret" not in response.text
    assert fake_db.rollbacks == 1


def test_chat_validation_rejects_invalid_history_shape_before_agent_execution(monkeypatch):
    app = build_app(chat_api.router)
    app.dependency_overrides[get_current_user] = authenticated_user

    called = False

    def should_not_run(*args, **kwargs):
        nonlocal called
        called = True
        return ChatResponse(
            conversationId="unused",
            message="unused",
            model="unused",
        )

    monkeypatch.setattr(chat_api, "run_identity_agent", should_not_run)

    client = TestClient(app)
    response = client.post(
        "/api/chat/",
        json={
            "message": "test",
            "history": [{"role": "user"}],
        },
    )

    assert response.status_code == 422
    assert called is False


def test_feedback_validation_rejects_non_positive_message_id():
    app = build_app(feedback_api.router)
    app.dependency_overrides[get_current_user] = authenticated_user

    client = TestClient(app)
    response = client.post(
        "/api/chat-feedback/",
        json={
            "conversationId": "conversation-1",
            "messageId": 0,
            "rating": "up",
        },
    )

    assert response.status_code == 422
