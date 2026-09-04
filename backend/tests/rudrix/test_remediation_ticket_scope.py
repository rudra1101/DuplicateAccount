from __future__ import annotations

from app.ai.tools import remediation_action_tools
from app.ai.tools.remediation_action_tools import (
    RudrixRemediationOperationsTool,
    normalize_remediation_arguments,
)


def _item(item_id: int, status: str, ticket_id: str | None = None):
    return {
        "id": item_id,
        "integrationId": 1,
        "integrationName": "Test Integration",
        "application": "Active Directory",
        "confidence": 97.0,
        "status": status,
        "ticketId": ticket_id,
        "ticketStatus": None,
        "account1Key": f"acct-{item_id}-1",
        "account2Key": f"acct-{item_id}-2",
        "account1": {"username": f"user{item_id}"},
        "account2": {"username": f"user{item_id}.dup"},
    }


def test_generic_remediation_search_defaults_to_pending_action():
    normalized = normalize_remediation_arguments(
        {
            "operation": "SEARCH",
            "search": None,
            "application": None,
            "status": None,
            "minimum_confidence": None,
            "limit": 10,
        }
    )

    assert normalized["status"] == "PENDING_ACTION"


def test_needs_ticket_scope_returns_only_pending_items_without_ticket(monkeypatch):
    seen = {}

    def fake_list(db, **kwargs):
        seen.update(kwargs)
        return [
            _item(1, "PENDING_ACTION", None),
            _item(2, "PENDING_ACTION", "REQ0010002"),
        ]

    monkeypatch.setattr(remediation_action_tools, "list_remediation_items", fake_list)

    tool = RudrixRemediationOperationsTool()
    result = tool.execute(
        db=object(),
        arguments={
            "operation": "SEARCH",
            "search": None,
            "application": None,
            "status": "NEEDS_TICKET",
            "minimum_confidence": None,
            "limit": 10,
        },
    )

    assert seen["status"] == "PENDING_ACTION"
    assert result["statusScope"] == "NEEDS_TICKET"
    assert result["totalMatching"] == 1
    assert result["returnedItems"] == 1
    assert result["items"][0]["remediationItemId"] == 1
    assert result["items"][0]["needsTicket"] is True


def test_actionable_scope_still_includes_pending_and_ticket_open(monkeypatch):
    def fake_list(db, **kwargs):
        return [
            _item(1, "PENDING_ACTION"),
            _item(2, "TICKET_OPEN", "REQ0010002"),
            _item(3, "ACTIONED", "REQ0010003"),
        ]

    monkeypatch.setattr(remediation_action_tools, "list_remediation_items", fake_list)

    tool = RudrixRemediationOperationsTool()
    result = tool.execute(
        db=object(),
        arguments={
            "operation": "SEARCH",
            "search": None,
            "application": None,
            "status": "ACTIONABLE",
            "minimum_confidence": None,
            "limit": 10,
        },
    )

    assert result["totalMatching"] == 2
    assert {item["status"] for item in result["items"]} == {
        "PENDING_ACTION",
        "TICKET_OPEN",
    }


def test_schema_exposes_needs_ticket_virtual_status():
    enum = RudrixRemediationOperationsTool.parameters["properties"]["status"]["enum"]
    assert "NEEDS_TICKET" in enum
    assert "ACTIONABLE" in enum
