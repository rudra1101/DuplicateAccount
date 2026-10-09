from types import SimpleNamespace

from app.ai.providers.base import ProviderResponse, ProviderToolCall
from app.schemas.chat import ChatRequest


def test_internal_state_leak_is_replaced_by_grounded_tool_result(monkeypatch):
    import app.ai.fast_agent_service as fast_agent

    class Provider:
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
                            arguments={"integration": "Active Directory", "limit": 20},
                        )
                    ],
                    model=model,
                )
            else:
                response = ProviderResponse(
                    text=(
                        "As Rudrix, the AI copilot for IdentityAI, the current structured "
                        "conversation state is: {'last_filters': {'context': 'orphan_accounts'}}. "
                        "What would you like to do next?"
                    ),
                    assistant_message={
                        "role": "assistant",
                        "content": (
                            "As Rudrix, the AI copilot for IdentityAI, the current structured "
                            "conversation state is: {'last_filters': {'context': 'orphan_accounts'}}."
                        ),
                    },
                    tool_calls=[],
                    model=model,
                )
            yield {"type": "result", "response": response}

    class Registry:
        def definitions(self):
            return [
                {
                    "name": "search_orphan_accounts",
                    "description": "Search current orphan accounts by integration.",
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
            return {
                "count": 1,
                "items": [
                    {
                        "sourceAccountId": 7,
                        "displayName": "Test Orphan",
                        "application": "Active Directory",
                        "integrationName": "Active Directory",
                        "employeeId": "W00999",
                        "orphanType": "UNMATCHED_ACCOUNT",
                        "reason": "NO_MATCH",
                    }
                ],
                "message": "Found 1 current orphan account(s).",
                "reportType": "orphan_accounts",
                "reportFilters": {"integrationId": 12},
            }

    provider = Provider()
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
    monkeypatch.setattr(fast_agent, "create_ai_tool_registry", lambda: Registry())

    events = list(
        fast_agent.run_identity_agent_stream_fast(
            db=object(),
            request=ChatRequest(message="show orphan accounts from Active Directory"),
            persisted_state={
                "last_filters": {
                    "context": "orphan_accounts",
                    "reportType": "orphan_accounts",
                    "filters": {"integrationId": 12},
                }
            },
        )
    )

    done = next(event for event in events if event["type"] == "done")
    message = done["response"].message

    assert "structured conversation state" not in message.lower()
    assert "last_filters" not in message
    assert "Found 1 current orphan account" in message
    assert "Test Orphan" in message


def test_state_instruction_marks_context_private():
    from app.ai.agent_core import AgentState
    from app.ai.fast_agent_service import _state_instruction

    instruction = _state_instruction(AgentState())
    assert "PRIVATE RUNTIME CONTEXT" in instruction
    assert "Never quote, summarize, mention, or expose" in instruction
