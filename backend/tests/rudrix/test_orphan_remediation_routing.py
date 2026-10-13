from __future__ import annotations

from app.ai.fast_agent_service import _select_definitions
from app.ai.tools import create_ai_tool_registry
from app.schemas.chat import ChatRequest


def _selected(message: str) -> set[str]:
    definitions = create_ai_tool_registry().definitions()
    request = ChatRequest(message=message, history=[])
    return {item["name"] for item in _select_definitions(definitions, request)}


def test_explicit_orphan_ticket_request_retrieves_orphan_write_capability():
    names = _selected("Create a remediation ticket to disable this orphan account")

    assert "create_orphan_remediation_ticket" in names
    assert "explain_orphan_account" in names or "search_orphan_accounts" in names


def test_orphan_ticket_preparation_without_action_still_retrieves_write_capability():
    names = _selected("Create a remediation ticket for Neha Verma orphan account")

    assert "create_orphan_remediation_ticket" in names
