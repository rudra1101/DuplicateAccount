from __future__ import annotations

from app.ai.agent_core.models import AgentEntity, AgentState, EntityType
from app.ai.agent_core.state import reduce_tool_result
from app.ai.fast_agent_service import _state_instruction


def _duplicate_state() -> AgentState:
    return AgentState(
        current_duplicate_candidate=AgentEntity(
            entity_type=EntityType.DUPLICATE_CANDIDATE,
            id=9694,
            label="asinha",
            attributes={
                "username": "asinha",
                "groupId": 2477,
                "account": {
                    "username": "asinha",
                    "employeeId": "W00003",
                    "email": "asinha@examplecorp.com",
                },
            },
            source="search_duplicate_groups",
        )
    )


def test_duplicate_context_is_available_to_agent_for_remediation_planning():
    rendered = _state_instruction(_duplicate_state())
    assert "9694" in rendered
    assert "asinha" in rendered
    assert "W00003" in rendered


def test_remediation_lookup_result_becomes_pending_action():
    state = reduce_tool_result(
        _duplicate_state(),
        tool_name="create_remediation_ticket",
        tool_result={
            "success": True,
            "data": {
                "created": False,
                "requiresInput": True,
                "remediationItemId": 73,
                "application": "Active Directory",
                "account1": {"username": "asinha.legacy"},
                "account2": {"username": "asinha"},
                "message": "Choose an account and action.",
            },
        },
    )

    assert state.current_remediation_item is not None
    assert state.current_remediation_item.id == 73
    assert state.pending_action is not None
    assert state.pending_action.capability == "create_remediation_ticket"
    assert state.pending_action.arguments["remediation_item_id"] == 73
    assert set(state.pending_action.missing_fields) == {"target", "action"}

    rendered = _state_instruction(state)
    assert "remediation_item_id" in rendered
    assert "73" in rendered
    assert "target" in rendered
    assert "action" in rendered


def test_successful_ticket_clears_pending_action():
    state = reduce_tool_result(
        _duplicate_state(),
        tool_name="create_remediation_ticket",
        tool_result={
            "success": True,
            "data": {
                "created": False,
                "requiresInput": True,
                "remediationItemId": 73,
            },
        },
    )
    assert state.pending_action is not None

    state = reduce_tool_result(
        state,
        tool_name="create_remediation_ticket",
        tool_result={
            "success": True,
            "data": {
                "remediationItemId": 73,
                "ticketId": "INC0012345",
                "status": "TICKET_OPEN",
            },
        },
    )

    assert state.pending_action is None
    assert state.current_remediation_item is not None
    assert state.current_remediation_item.attributes["ticketId"] == "INC0012345"
