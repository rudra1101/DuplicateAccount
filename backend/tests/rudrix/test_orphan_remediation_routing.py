from __future__ import annotations

from app.ai.agent_core.models import AgentEntity, AgentState, EntityType, PendingAction
from app.ai.fast_agent_service import _select_definitions
from app.ai.tools import create_ai_tool_registry
from app.schemas.chat import ChatRequest


def _selected(message: str, state: AgentState | None = None) -> set[str]:
    definitions = create_ai_tool_registry().definitions()
    request = ChatRequest(message=message, history=[])
    return {
        item["name"]
        for item in _select_definitions(definitions, request, state)
    }


def _neha_orphan_state() -> AgentState:
    return AgentState(
        current_account=AgentEntity(
            entity_type=EntityType.SOURCE_ACCOUNT,
            id=208,
            label="Neha Verma",
            attributes={
                "sourceAccountId": 208,
                "displayName": "Neha Verma",
                "employeeId": "W90008",
                "application": "Active Directory",
                "orphaned": True,
                "orphanType": "UNMATCHED_ACCOUNT",
            },
            source="explain_orphan_account",
        )
    )


def test_explicit_orphan_ticket_request_retrieves_orphan_write_capability():
    names = _selected("Create a remediation ticket to disable this orphan account")

    assert "create_orphan_remediation_ticket" in names
    assert "explain_orphan_account" in names or "search_orphan_accounts" in names


def test_orphan_ticket_preparation_without_action_still_retrieves_write_capability():
    names = _selected("Create a remediation ticket for Neha Verma orphan account")

    assert "create_orphan_remediation_ticket" in names


def test_referential_ticket_request_uses_grounded_orphan_context_for_retrieval():
    names = _selected(
        "Create a remediation ticket for her",
        _neha_orphan_state(),
    )

    assert "create_orphan_remediation_ticket" in names


def test_pending_orphan_action_keeps_write_capability_available_for_disable_followup():
    state = _neha_orphan_state()
    state.pending_action = PendingAction(
        capability="create_orphan_remediation_ticket",
        arguments={"source_account_id": 208},
        missing_fields=["action"],
    )

    names = _selected("Disable it", state)

    assert "create_orphan_remediation_ticket" in names
