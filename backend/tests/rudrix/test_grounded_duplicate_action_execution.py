from __future__ import annotations

from app.ai.agent_core.grounded_actions import resolve_grounded_action
from app.ai.agent_core.models import AgentEntity, AgentState, EntityType
from app.ai.fast_agent_service import run_identity_agent_stream_fast
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


def test_resolves_referential_duplicate_confirmation_from_grounded_state():
    action = resolve_grounded_action("confirm it", _state())

    assert action is not None
    assert action.tool_name == "review_duplicate_candidate"
    assert action.arguments["candidate_id"] == 9694
    assert action.arguments["decision"] == "DUPLICATE"


def test_resolves_explicit_duplicate_review_decisions():
    assert resolve_grounded_action("mark it as duplicate", _state()).arguments["decision"] == "DUPLICATE"
    assert resolve_grounded_action("mark it as not a duplicate", _state()).arguments["decision"] == "NOT_DUPLICATE"
    assert resolve_grounded_action("mark it uncertain", _state()).arguments["decision"] == "UNCERTAIN"


def test_does_not_execute_without_a_grounded_candidate():
    assert resolve_grounded_action("confirm it", AgentState()) is None


def test_fast_agent_executes_grounded_review_without_model_round_trip(monkeypatch):
    class FakeProvider:
        def stream_chat(self, **kwargs):
            raise AssertionError("grounded review must not call the model")

    class FakeRegistry:
        def definitions(self):
            return [
                {
                    "name": "review_duplicate_candidate",
                    "description": "review",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                }
            ]

        def execute(self, *, name, db, arguments):
            assert name == "review_duplicate_candidate"
            assert arguments["candidate_id"] == 9694
            assert arguments["decision"] == "DUPLICATE"
            return {
                "message": "Marked candidate **9694** as **DUPLICATE**.",
                "candidateId": 9694,
                "decision": "DUPLICATE",
            }

    monkeypatch.setattr(
        "app.ai.fast_agent_service.AIProviderFactory.create",
        lambda settings: FakeProvider(),
    )
    monkeypatch.setattr(
        "app.ai.fast_agent_service.create_ai_tool_registry",
        lambda: FakeRegistry(),
    )

    request = ChatRequest(message="confirm it", conversationId="conversation-1")
    events = list(
        run_identity_agent_stream_fast(
            db=object(),
            request=request,
            persisted_state=_state().model_dump(exclude_none=True),
        )
    )

    done = next(event for event in events if event["type"] == "done")
    response = done["response"]

    assert response.message == "Marked candidate **9694** as **DUPLICATE**."
    assert response.toolsUsed[0].name == "review_duplicate_candidate"
    assert response.toolsUsed[0].arguments["candidate_id"] == 9694
