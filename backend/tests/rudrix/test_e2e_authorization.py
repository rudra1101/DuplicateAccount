from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai import agent_service
from app.ai.providers.base import ProviderResponse, ProviderToolCall
from app.ai.tools.integration_tools import ListIntegrationsTool
from app.ai.tools.knowledge_tools import SearchKnowledgeBaseTool
from app.ai.tools.training_tools import GetTrainingLabelSummaryTool
from app.api import chat as chat_api
from app.api import chat_stream as stream_api
from app.auth.middleware import authentication_middleware
import app.auth.middleware as auth_middleware
from app.database.session import get_db


class FakeRequestDb:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeAuthDb:
    def __init__(self, user):
        self.user = user

    def get(self, model, user_id):
        return self.user if int(user_id) == int(self.user.id) else None

    def close(self):
        pass


class ScriptedProvider:
    def __init__(self, steps: list[dict[str, Any]], stream_text: str | None = None):
        self.steps = list(steps)
        self.stream_text = stream_text
        self.tool_definition_history: list[set[str]] = []

    def _response(self, *, model: str, step: dict[str, Any]) -> ProviderResponse:
        text = str(step.get("text") or "")
        tool_name = step.get("tool_name")
        arguments = dict(step.get("arguments") or {})
        tool_calls = []
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": text,
        }

        if tool_name:
            tool_calls = [
                ProviderToolCall(
                    name=tool_name,
                    arguments=arguments,
                )
            ]
            assistant_message["tool_calls"] = [
                {
                    "name": tool_name,
                    "arguments": arguments,
                }
            ]

        return ProviderResponse(
            text=text,
            assistant_message=assistant_message,
            tool_calls=tool_calls,
            model=model,
        )

    def chat(self, *, model: str, messages, tools):
        self.tool_definition_history.append(
            {definition["name"] for definition in tools}
        )
        if not self.steps:
            raise AssertionError("Unexpected extra Rudrix provider call")
        return self._response(model=model, step=self.steps.pop(0))

    def stream_chat(self, *, model: str, messages, tools):
        self.tool_definition_history.append(
            {definition["name"] for definition in tools}
        )

        if self.steps:
            step = self.steps.pop(0)
            response = self._response(model=model, step=step)
            if response.tool_calls:
                yield {"type": "result", "response": response}
                return

        if self.stream_text is None:
            raise AssertionError("Unexpected streaming provider call")

        response = ProviderResponse(
            text=self.stream_text,
            assistant_message={"role": "assistant", "content": self.stream_text},
            tool_calls=[],
            model=model,
        )
        yield {"type": "delta", "text": self.stream_text}
        yield {"type": "result", "response": response}

    def embed(self, *, model: str, inputs: list[str]):
        raise AssertionError("Embedding should not run in E2E authorization tests")


def role_user(*permissions: str, role: str = "USER"):
    role_record = SimpleNamespace(
        permissions=[SimpleNamespace(code=code) for code in permissions]
    )
    return SimpleNamespace(
        id=7,
        username="rbac-e2e-user",
        role=role,
        role_record=role_record,
        is_active=True,
    )


def owner_user():
    return SimpleNamespace(
        id=1,
        username="owner",
        role="OWNER",
        role_record=None,
        is_active=True,
    )


def build_authenticated_app(monkeypatch, *, user, router, request_db):
    app = FastAPI()
    app.middleware("http")(authentication_middleware)
    app.include_router(router, prefix="/api")

    monkeypatch.setattr(
        auth_middleware,
        "decode_access_token",
        lambda token: {"sub": str(user.id)},
    )
    monkeypatch.setattr(
        auth_middleware,
        "SessionLocal",
        lambda: FakeAuthDb(user),
    )
    app.dependency_overrides[get_db] = lambda: request_db
    return app


def install_provider(monkeypatch, provider):
    monkeypatch.setattr(
        agent_service.AIProviderFactory,
        "create",
        lambda settings: provider,
    )


def patch_normal_chat_persistence(monkeypatch):
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


def patch_stream_persistence(monkeypatch):
    monkeypatch.setattr(
        stream_api,
        "get_or_create_chat_conversation",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        stream_api,
        "save_chat_message",
        lambda *args, **kwargs: SimpleNamespace(id=101),
    )


def authenticated_client(app):
    client = TestClient(app)
    client.cookies.set("identityai_access_token", "e2e-test-token")
    return client


def test_http_user_with_integration_view_can_execute_integration_tool(monkeypatch):
    user = role_user("integration.view")
    request_db = FakeRequestDb()
    app = build_authenticated_app(
        monkeypatch,
        user=user,
        router=chat_api.router,
        request_db=request_db,
    )
    patch_normal_chat_persistence(monkeypatch)

    provider = ScriptedProvider(
        [
            {
                "tool_name": "list_integrations",
                "arguments": {"enabled_only": True},
            },
            {"text": "There is 1 enabled integration."},
        ]
    )
    install_provider(monkeypatch, provider)

    calls = []

    def execute(self, *, db, arguments):
        calls.append(dict(arguments))
        return {
            "count": 1,
            "integrations": [{"name": "Active Directory"}],
        }

    monkeypatch.setattr(ListIntegrationsTool, "execute", execute)

    response = authenticated_client(app).post(
        "/api/chat/",
        json={"message": "How many enabled integrations do we have?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["toolsUsed"][0]["result"]["success"] is True
    assert calls == [{"enabled_only": True}]
    assert "list_integrations" in provider.tool_definition_history[0]


def test_http_user_without_ml_view_cannot_execute_training_tool(monkeypatch):
    user = role_user("integration.view")
    request_db = FakeRequestDb()
    app = build_authenticated_app(
        monkeypatch,
        user=user,
        router=chat_api.router,
        request_db=request_db,
    )
    patch_normal_chat_persistence(monkeypatch)

    provider = ScriptedProvider(
        [
            {
                "tool_name": "get_training_label_summary",
                "arguments": {},
            },
            {"text": "You do not have access to training data."},
        ]
    )
    install_provider(monkeypatch, provider)

    response = authenticated_client(app).post(
        "/api/chat/",
        json={"message": "How many training labels do we have?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["toolsUsed"][0]["result"]["success"] is False
    assert body["toolsUsed"][0]["result"]["error"] == "Access denied."
    assert "get_training_label_summary" not in provider.tool_definition_history[0]


def test_http_user_without_knowledge_view_cannot_execute_rag_tool(monkeypatch):
    user = role_user("integration.view")
    request_db = FakeRequestDb()
    app = build_authenticated_app(
        monkeypatch,
        user=user,
        router=chat_api.router,
        request_db=request_db,
    )
    patch_normal_chat_persistence(monkeypatch)

    provider = ScriptedProvider(
        [
            {
                "tool_name": "search_knowledge_base",
                "arguments": {"query": "policy", "document_id": None, "top_k": 3},
            },
            {"text": "You do not have access to knowledge data."},
        ]
    )
    install_provider(monkeypatch, provider)

    response = authenticated_client(app).post(
        "/api/chat/",
        json={"message": "What does our policy say?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["toolsUsed"][0]["result"]["success"] is False
    assert body["toolsUsed"][0]["result"]["error"] == "Access denied."
    assert "search_knowledge_base" not in provider.tool_definition_history[0]


def test_http_owner_can_access_all_mapped_rudrix_tools(monkeypatch):
    user = owner_user()
    request_db = FakeRequestDb()
    app = build_authenticated_app(
        monkeypatch,
        user=user,
        router=chat_api.router,
        request_db=request_db,
    )
    patch_normal_chat_persistence(monkeypatch)

    provider = ScriptedProvider(
        [
            {
                "tool_name": "get_training_label_summary",
                "arguments": {},
            },
            {"text": "Training labels are available."},
        ]
    )
    install_provider(monkeypatch, provider)

    calls = []

    def execute(self, *, db, arguments):
        calls.append(dict(arguments))
        return {"totalLabels": 10}

    monkeypatch.setattr(GetTrainingLabelSummaryTool, "execute", execute)

    response = authenticated_client(app).post(
        "/api/chat/",
        json={"message": "How many training labels do we have?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["toolsUsed"][0]["result"]["success"] is True
    assert calls == [{}]
    assert "get_training_label_summary" in provider.tool_definition_history[0]


def test_streaming_user_with_integration_view_has_same_tool_access(
    monkeypatch,
):
    user = role_user("integration.view")
    request_db = FakeRequestDb()
    app = build_authenticated_app(
        monkeypatch,
        user=user,
        router=stream_api.router,
        request_db=request_db,
    )
    patch_stream_persistence(monkeypatch)

    provider = ScriptedProvider(
        [
            {
                "tool_name": "list_integrations",
                "arguments": {"enabled_only": True},
            },
        ],
        stream_text="There is 1 enabled integration.",
    )
    install_provider(monkeypatch, provider)

    calls = []

    def execute(self, *, db, arguments):
        calls.append(dict(arguments))
        return {
            "count": 1,
            "integrations": [{"name": "Active Directory"}],
        }

    monkeypatch.setattr(ListIntegrationsTool, "execute", execute)

    response = authenticated_client(app).post(
        "/api/chat/stream",
        json={"message": "How many enabled integrations do we have?"},
    )

    assert response.status_code == 200
    events = [
        json.loads(line)
        for line in response.text.splitlines()
        if line.strip()
    ]
    assert events[0]["type"] == "start"
    assert any(
        event.get("type") == "delta"
        and event.get("text") == "There is 1 enabled integration."
        for event in events
    )
    done = events[-1]
    assert done["type"] == "done"
    assert done["toolsUsed"][0]["name"] == "list_integrations"
    assert done["toolsUsed"][0]["result"]["success"] is True
    assert calls == [{"enabled_only": True}]
    assert request_db.commits == 1


def test_streaming_user_without_integration_view_cannot_execute_tool(
    monkeypatch,
):
    user = role_user("dashboard.view")
    request_db = FakeRequestDb()
    app = build_authenticated_app(
        monkeypatch,
        user=user,
        router=stream_api.router,
        request_db=request_db,
    )
    patch_stream_persistence(monkeypatch)

    provider = ScriptedProvider(
        [
            {
                "tool_name": "list_integrations",
                "arguments": {"enabled_only": False},
            },
        ],
        stream_text="You do not have access to integration data.",
    )
    install_provider(monkeypatch, provider)

    calls = []

    def execute(self, *, db, arguments):
        calls.append(dict(arguments))
        return {"count": 1000}

    monkeypatch.setattr(ListIntegrationsTool, "execute", execute)

    response = authenticated_client(app).post(
        "/api/chat/stream",
        json={"message": "List all integrations."},
    )

    assert response.status_code == 200
    events = [
        json.loads(line)
        for line in response.text.splitlines()
        if line.strip()
    ]
    done = events[-1]
    assert done["type"] == "done"
    assert done["toolsUsed"][0]["result"]["success"] is False
    assert done["toolsUsed"][0]["result"]["error"] == "Access denied."
    assert calls == []
    assert "list_integrations" not in provider.tool_definition_history[0]
