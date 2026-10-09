from __future__ import annotations

from types import SimpleNamespace

from app.ai.agent_core.models import AgentEntity, AgentState, EntityType
from app.ai.fast_agent_service import run_identity_agent_stream_fast
from app.ai.providers.base import ProviderResponse, ProviderToolCall
from app.schemas.chat import ChatRequest


def _state() -> AgentState:
    return AgentState(
        current_duplicate_candidate=AgentEntity(
            entity_type=EntityType.DUPLICATE_CANDIDATE,
            id=9694,
            label="asinha",
            attributes={"groupId": 2477, "confidence": 97},
            source="search_duplicate_groups",
        )
    )


def test_generic_agent_receives_grounded_candidate_and_executes_model_selected_review(monkeypatch):
    class FakeProvider:
        def __init__(self):
            self.calls = 0

        def stream_chat(self, *, model, messages, tools):
            self.calls += 1
            if self.calls == 1:
                assert "9694" in str(messages)
                assert any(item.get("name") == "review_duplicate_candidate" for item in tools)
                response = ProviderResponse(
                    text="",
                    assistant_message={"role": "assistant", "content": ""},
                    tool_calls=[
                        ProviderToolCall(
                            name="review_duplicate_candidate",
                            arguments={
                                "candidate_id": 9694,
                                "decision": "DUPLICATE",
                                "comment": None,
                            },
                        )
                    ],
                    model=model,
                )
            else:
                response = ProviderResponse(
                    text="Marked candidate 9694 as DUPLICATE.",
                    assistant_message={
                        "role": "assistant",
                        "content": "Marked candidate 9694 as DUPLICATE.",
                    },
                    tool_calls=[],
                    model=model,
                )
            yield {"type": "result", "response": response}

    class FakeRegistry:
        def definitions(self):
            return [
                {
                    "name": "review_duplicate_candidate",
                    "description": "Record a duplicate review decision for a grounded candidate.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                }
            ]

        def execute(self, *, name, db, arguments):
            assert name == "review_duplicate_candidate"
            assert arguments["candidate_id"] == 9694
            assert arguments["decision"] == "DUPLICATE"
            return {
                "message": "Marked candidate 9694 as DUPLICATE.",
                "candidateId": 9694,
                "decision": "DUPLICATE",
            }

    provider = FakeProvider()
    monkeypatch.setattr(
        "app.ai.fast_agent_service.get_ai_settings",
        lambda: SimpleNamespace(
            fast_model="fast-model",
            reasoning_model="reasoning-model",
            max_tool_iterations=4,
        ),
    )
    monkeypatch.setattr(
        "app.ai.fast_agent_service.AIProviderFactory.create",
        lambda settings: provider,
    )
    monkeypatch.setattr(
        "app.ai.fast_agent_service.create_ai_tool_registry",
        lambda: FakeRegistry(),
    )

    events = list(
        run_identity_agent_stream_fast(
            db=object(),
            request=ChatRequest(message="confirm it", conversationId="conversation-1"),
            persisted_state=_state().model_dump(exclude_none=True),
        )
    )

    done = next(event for event in events if event["type"] == "done")
    response = done["response"]
    assert response.message == "Marked candidate 9694 as DUPLICATE."
    assert response.toolsUsed[0].name == "review_duplicate_candidate"
    assert provider.calls == 2
