from __future__ import annotations

from app.ai.agent_core.models import AgentEntity, AgentState, EntityType
from app.ai.fast_agent_service import _apply_grounded_state_arguments


def test_grounded_state_fills_referential_duplicate_review_candidate():
    state = AgentState(
        current_duplicate_candidate=AgentEntity(
            entity_type=EntityType.DUPLICATE_CANDIDATE,
            id=9694,
            label="asinha",
            attributes={"groupId": 2477, "username": "asinha", "confidence": 97},
            source="search_duplicate_groups",
        )
    )
    tool_calls = [
        {
            "name": "review_duplicate_candidate",
            "arguments": {"candidate_id": None, "decision": "DUPLICATE"},
        }
    ]

    _apply_grounded_state_arguments(tool_calls=tool_calls, state=state)

    assert tool_calls[0]["arguments"]["candidate_id"] == 9694


def test_grounded_state_does_not_override_explicit_candidate_id():
    state = AgentState(
        current_duplicate_candidate=AgentEntity(
            entity_type=EntityType.DUPLICATE_CANDIDATE,
            id=9694,
            label="asinha",
            source="search_duplicate_groups",
        )
    )
    tool_calls = [
        {
            "name": "review_duplicate_candidate",
            "arguments": {"candidate_id": 1234, "decision": "DUPLICATE"},
        }
    ]

    _apply_grounded_state_arguments(tool_calls=tool_calls, state=state)

    assert tool_calls[0]["arguments"]["candidate_id"] == 1234
