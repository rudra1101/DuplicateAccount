from __future__ import annotations

from types import SimpleNamespace

from app.ai.providers.base import ProviderResponse, ProviderToolCall
from app.schemas.chat import ChatRequest


class _FakeProvider:
    def __init__(self) -> None:
        self.stream_calls = 0
        self.plan_calls = 0

    def stream_chat(self, *, model, messages, tools):
        self.stream_calls += 1
        names = {item.get("name") for item in tools}
        assert "search_orphan_accounts" in names
        assert "search_identityai_product_knowledge" in names

        if self.stream_calls == 1:
            response = ProviderResponse(
                text="",
                assistant_message={"role": "assistant", "content": ""},
                tool_calls=[
                    ProviderToolCall(
                        name="search_identityai_product_knowledge",
                        arguments={"query": "orphan accounts"},
                    )
                ],
                model=model,
            )
        elif self.stream_calls == 2:
            response = ProviderResponse(
                text=(
                    "I'm Rudrix, your AI copilot for IdentityAI. "
                    "What would you like to accomplish?"
                ),
                assistant_message={
                    "role": "assistant",
                    "content": "What would you like to accomplish?",
                },
                tool_calls=[],
                model=model,
            )
        else:
            response = ProviderResponse(
                text=(
                    "I'm Rudrix, your AI copilot for IdentityAI. "
                    "What's your goal today?"
                ),
                assistant_message={
                    "role": "assistant",
                    "content": "What's your goal today?",
                },
                tool_calls=[],
                model=model,
            )

        yield {"type": "result", "response": response}

    def chat(self, *, model, messages, tools):
        self.plan_calls += 1
        assert len(tools) == 1
        assert tools[0].get("name") == "search_orphan_accounts"
        return ProviderResponse(
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


class _FakeRegistry:
    def definitions(self):
        return [
            {
                "name": "search_orphan_accounts",
                "description": (
                    "Search current orphan accounts by integration or application. "
                    "Use for current orphan account records and filters."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "integration": {"type": ["string", "null"]},
                        "limit": {"type": "integer"},
                    },
                    "required": [],
                },
            },
            {
                "name": "search_identityai_product_knowledge",
                "description": "Explain IdentityAI product behavior and features.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        ]

    def execute(self, *, name, db, arguments):
        if name == "search_identityai_product_knowledge":
            return {
                "message": "Orphan accounts are accounts without a valid identity correlation.",
                "items": [],
            }

        assert name == "search_orphan_accounts"
        assert arguments["integration"] == "Active Directory"
        return {
            "count": 2,
            "items": [
                {"sourceAccountId": 1, "username": "orphan.one", "application": "Active Directory"},
                {"sourceAccountId": 2, "username": "orphan.two", "application": "Active Directory"},
            ],
            "message": "Found 2 current orphan account(s).",
        }


def test_agent_requires_primary_grounding_after_unrelated_success(monkeypatch):
    import app.ai.fast_agent_service as fast_agent

    provider = _FakeProvider()
    monkeypatch.setattr(
        fast_agent,
        "get_ai_settings",
        lambda: SimpleNamespace(
            fast_model="fast-model",
            reasoning_model="reasoning-model",
            max_tool_iterations=5,
        ),
    )
    monkeypatch.setattr(fast_agent.AIProviderFactory, "create", lambda settings: provider)
    monkeypatch.setattr(fast_agent, "create_ai_tool_registry", lambda: _FakeRegistry())

    events = list(
        fast_agent.run_identity_agent_stream_fast(
            db=object(),
            request=ChatRequest(message="show orphan accounts from Active Directory"),
        )
    )

    done = next(event for event in events if event["type"] == "done")
    response = done["response"]

    assert provider.stream_calls == 3
    assert provider.plan_calls == 1
    assert "What would you like to accomplish" not in response.message
    assert "What's your goal today" not in response.message
    assert response.message.startswith("Found 2 current orphan account(s).")
    assert [item.name for item in response.toolsUsed] == [
        "search_identityai_product_knowledge",
        "search_orphan_accounts",
    ]
    assert response.toolsUsed[-1].result["success"] is True


def test_all_failed_live_tools_return_grounded_failure_not_zero_results(monkeypatch):
    import app.ai.fast_agent_service as fast_agent

    class FailureProvider:
        def __init__(self):
            self.calls = 0
            self.plan_calls = 0

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

        def chat(self, *, model, messages, tools):
            self.plan_calls += 1
            assert len(tools) == 1
            assert tools[0].get("name") == "search_orphan_accounts"
            return ProviderResponse(
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

    class FailureRegistry(_FakeRegistry):
        def execute(self, *, name, db, arguments):
            if name == "search_orphan_accounts":
                raise RuntimeError("database connection unavailable")
            return super().execute(name=name, db=db, arguments=arguments)

    provider = FailureProvider()
    monkeypatch.setattr(
        fast_agent,
        "get_ai_settings",
        lambda: SimpleNamespace(
            fast_model="fast-model",
            reasoning_model="reasoning-model",
            max_tool_iterations=4,
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

    assert provider.plan_calls == 1
    assert "No result was treated as an empty data set" in done["response"].message
    assert "No orphan accounts were found" not in done["response"].message
