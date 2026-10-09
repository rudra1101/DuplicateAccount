from __future__ import annotations

from app.ai.agent_core.models import AgentState, PendingAction
from app.ai.authorization import reset_rudrix_permissions, set_rudrix_permissions
from app.ai.fast_agent_service import _state_instruction
from app.ai.tools import create_ai_tool_registry


def _pending_ticket_state() -> AgentState:
    return AgentState(
        pending_action=PendingAction(
            capability="create_remediation_ticket",
            arguments={
                "remediation_item_id": 1,
                "target": "ACCOUNT_2",
                "action": "DELETE",
            },
            requires_confirmation=True,
            missing_fields=[],
        )
    )


def test_pending_ticket_context_is_structured_not_parsed_from_assistant_prose():
    rendered = _state_instruction(_pending_ticket_state())

    assert "create_remediation_ticket" in rendered
    assert "remediation_item_id" in rendered
    assert "ACCOUNT_2" in rendered
    assert "DELETE" in rendered


def test_ticket_creation_capability_requires_remediation_manage():
    token = set_rudrix_permissions({"remediation.view"})
    try:
        names = {
            item["name"]
            for item in create_ai_tool_registry().definitions()
        }
    finally:
        reset_rudrix_permissions(token)

    assert "search_remediation_items" in names
    assert "create_remediation_ticket" not in names


def test_ticket_creation_capability_is_exposed_when_authorized():
    token = set_rudrix_permissions({"remediation.view", "remediation.manage"})
    try:
        names = {
            item["name"]
            for item in create_ai_tool_registry().definitions()
        }
    finally:
        reset_rudrix_permissions(token)

    assert "search_remediation_items" in names
    assert "create_remediation_ticket" in names
