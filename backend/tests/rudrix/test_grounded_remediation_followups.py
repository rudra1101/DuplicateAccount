from __future__ import annotations

from app.ai.agent_core.grounded_actions import resolve_grounded_action
from app.ai.agent_core.models import AgentEntity, AgentState, EntityType
from app.ai.agent_core.state import reduce_tool_result


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


def test_create_ticket_for_current_duplicate_uses_grounded_reference():
    action = resolve_grounded_action("create a ticket for it", _duplicate_state())

    assert action is not None
    assert action.tool_name == "create_remediation_ticket"
    assert action.arguments == {
        "remediation_item_id": None,
        "account_reference": "asinha",
        "target": None,
        "action": None,
    }


def test_remediation_lookup_result_becomes_pending_action():
    state = _duplicate_state()
    state = reduce_tool_result(
        state,
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


def test_delete_second_account_completes_pending_ticket_without_internal_ids():
    state = _duplicate_state()
    state = reduce_tool_result(
        state,
        tool_name="create_remediation_ticket",
        tool_result={
            "success": True,
            "data": {
                "created": False,
                "requiresInput": True,
                "remediationItemId": 73,
                "account1": {"username": "asinha.legacy"},
                "account2": {"username": "asinha"},
            },
        },
    )

    action = resolve_grounded_action("delete second account", state)

    assert action is not None
    assert action.tool_name == "create_remediation_ticket"
    assert action.arguments["remediation_item_id"] == 73
    assert action.arguments["target"] == "ACCOUNT_2"
    assert action.arguments["action"] == "DELETE"
    assert action.arguments["account_reference"] is None


def test_successful_ticket_clears_pending_action():
    state = _duplicate_state()
    state = reduce_tool_result(
        state,
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
