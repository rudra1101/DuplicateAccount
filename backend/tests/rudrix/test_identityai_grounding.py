from __future__ import annotations

from types import SimpleNamespace

from app.ai.providers.base import ProviderResponse, ProviderToolCall
from app.schemas.chat import ChatRequest


class _FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def stream_chat(self, *, model, messages, tools):
        self.calls += 1
        names = {item.get("name") for item in tools}
        assert "search_orphan_accounts" in names

        if self.calls == 1:
            response = ProviderResponse(
                text="The current data could not be retrieved.",
                assistant_message={
                    "role": "assistant",
                    "content": "The current data could not be retrieved.",
                },
                tool_calls=[],
                model=model,
            )
        elif self.calls == 2:
            response = ProviderResponse(
                text="",
                assistant_message={"role": "assistant", "content": ""},
                tool_calls=[
                    ProviderToolCall(
                        name="search_orphan_accounts",
                        arguments={"integration": "Active Directory", "limit": 20},
                    )
                ],
                model=model,
            )
        else:
            response = ProviderResponse(
                text="Found 2 current orphan accounts in Active Directory.",
                assistant_message={
                    "role": "assistant",
                    "content": "Found 2 current orphan accounts in Active Directory.",
                },
                tool_calls=[],
                model=model,
            )

        yield {"type": "result", "response": response}


class _FakeRegistry:
    def definitions(self):
        return [
            {
                "name": "search_orphan_accounts",
                "description": "Search current orphan accounts by integration or application.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "integration": {"type": ["string", "null"]},
                        "limit": {"type": "integer"},
                    },
                    "required": [],
                },
            }
        ]

    def execute(self, *, name, db, arguments):
        assert name == "search_orphan_accounts"
        assert arguments["integration"] == "Active Directory"
        return {
            "count": 2,
            "items": [
                {"sourceAccountId": 1, "username": "orphan.one"},
                {"sourceAccountId": 2, "username": "orphan.two"},
            ],
            "message": "Found 2 current orphan account(s).",
        }


def test_agent_does_not_accept_ungrounded_data_unavailable_answer(monkeypatch):
    import app.ai.fast_agent_service as fast_agent

    provider = _FakeProvider()
    monkeypatch.setattr(
        fast_agent,
        "get_ai_settings",
        lambda: SimpleNamespace(
            fast_model="fast-model",
            reasoning_model="reasoning-model",
            max_tool_iterations=4,
        ),
    )
    monkeypatch.setattr(
        fast_agent.AIProviderFactory,
        "create",
        lambda settings: provider,
    )
    monkeypatch.setattr(
        fast_agent,
        "create_ai_tool_registry",
        lambda: _FakeRegistry(),
    )

    events = list(
        fast_agent.run_identity_agent_stream_fast(
            db=object(),
            request=ChatRequest(message="show orphan accounts from Active Directory"),
        )
    )

    done = next(event for event in events if event["type"] == "done")
    response = done["response"]

    assert provider.calls == 3
    assert response.message == "Found 2 current orphan accounts in Active Directory."
    assert response.toolsUsed[0].name == "search_orphan_accounts"
    assert response.toolsUsed[0].result["success"] is True


def test_all_failed_live_tools_return_grounded_failure_not_zero_results(monkeypatch):
    import app.ai.fast_agent_service as fast_agent

    class FailureProvider:
        def __init__(self):
            self.calls = 0

        def stream_chat(self, *, model, messages, tools):
            self.calls += 1
            if self.calls == 1:
                response = ProviderResponse(
                    text="",
                    assistant_message={"role": "assistant", "content": ""},
                    tool_calls=[
                        ProviderToolCall(
                            name="search_orphan_accounts",
                            arguments={"integration": "Active Directory"},
                        )
                    ],
                    model=model,
                )
            else:
                response = ProviderResponse(
                    text="No orphan accounts were found.",
                    assistant_message={
                        "role": "assistant",
                        "content": "No orphan accounts were found.",
                    },
                    tool_calls=[],
                    model=model,
                )
            yield {"type": "result", "response": response}

    class FailureRegistry(_FakeRegistry):
        def execute(self, *, name, db, arguments):
            raise RuntimeError("database connection unavailable")

    provider = FailureProvider()
    monkeypatch.setattr(
        fast_agent,
        "get_ai_settings",
        lambda: SimpleNamespace(
            fast_model="fast-model",
            reasoning_model="reasoning-model",
            max_tool_iterations=3,
        ),
    )
    monkeypatch.setattr(fast_agent.AIProviderFactory, "create", lambda settings: provider)
    monkeypatch.setattr(fast_agent, "create_ai_tool_registry", lambda: FailureRegistry())

    events = list(
        fast_agent.run_identity_agent_stream_fast(
            db=object(),
            request=ChatRequest(message="show orphan accounts from Active Directory"),
        )
    )
    done = next(event for event in events if event["type"] == "done")

    assert "No result was treated as an empty data set" in done["response"].message
    assert "No orphan accounts were found" not in done["response"].message
