from __future__ import annotations

from app.ai.tools.remediation_action_tools import (
    RudrixRemediationOperationsTool,
    normalize_remediation_arguments,
)


def test_null_like_remediation_arguments_default_search_to_actionable():
    normalized = normalize_remediation_arguments(
        {
            "operation": "null",
            "search": "None",
            "application": "null",
            "status": "null",
            "minimum_confidence": "null",
            "limit": "undefined",
            "item_id": "",
            "comment": "n/a",
        }
    )

    assert normalized == {
        "operation": "SEARCH",
        "search": None,
        "application": None,
        "status": "ACTIONABLE",
        "minimum_confidence": None,
        "limit": 10,
        "item_id": None,
        "comment": None,
    }


def test_explicit_all_status_is_preserved():
    normalized = normalize_remediation_arguments(
        {
            "operation": "search",
            "status": "all",
        }
    )

    assert normalized["operation"] == "SEARCH"
    assert normalized["status"] == "ALL"


def test_numeric_remediation_filters_are_safely_coerced():
    normalized = normalize_remediation_arguments(
        {
            "operation": "search",
            "minimum_confidence": "95",
            "limit": "500",
            "item_id": "12",
        }
    )

    assert normalized["operation"] == "SEARCH"
    assert normalized["status"] == "ACTIONABLE"
    assert normalized["minimum_confidence"] == 95.0
    assert normalized["limit"] == 50
    assert normalized["item_id"] == 12


def test_actionable_search_excludes_ignored_actioned_and_failed(monkeypatch):
    from app.ai.tools import remediation_action_tools

    def fake_list_remediation_items(db, **kwargs):
        del db, kwargs
        return [
            {
                "id": 1,
                "application": "Active Directory",
                "status": "PENDING_ACTION",
                "confidence": 97.0,
                "account1Key": "ad:a1",
                "account2Key": "ad:a2",
                "account1": {"username": "alice"},
                "account2": {"username": "alice.old"},
            },
            {
                "id": 2,
                "application": "ServiceNow",
                "status": "TICKET_OPEN",
                "confidence": 96.0,
                "ticketId": "REQ0010001",
                "account1Key": "sn:b1",
                "account2Key": "sn:b2",
                "account1": {"username": "bob"},
                "account2": {"username": "bob.old"},
            },
            {"id": 3, "application": "ServiceNow", "status": "IGNORED"},
            {"id": 4, "application": "ServiceNow", "status": "ACTIONED"},
            {"id": 5, "application": "ServiceNow", "status": "FAILED"},
        ]

    monkeypatch.setattr(
        remediation_action_tools,
        "list_remediation_items",
        fake_list_remediation_items,
    )

    result = RudrixRemediationOperationsTool().execute(
        db=object(),
        arguments={
            "search": None,
            "application": None,
            "status": None,
            "minimum_confidence": None,
            "limit": 10,
        },
    )

    assert result["statusScope"] == "ACTIONABLE"
    assert result["actionableStatuses"] == ["PENDING_ACTION", "TICKET_OPEN"]
    assert result["totalMatching"] == 2
    assert result["returnedItems"] == 2
    assert result["count"] == 2
    assert [item["status"] for item in result["items"]] == [
        "PENDING_ACTION",
        "TICKET_OPEN",
    ]


def test_total_matching_is_not_limited_to_returned_rows(monkeypatch):
    from app.ai.tools import remediation_action_tools

    def fake_list_remediation_items(db, **kwargs):
        del db, kwargs
        return [
            {
                "id": index,
                "application": "Active Directory",
                "status": "PENDING_ACTION",
                "confidence": 97.0,
                "account1Key": f"ad:a{index}",
                "account2Key": f"ad:b{index}",
                "account1": {"username": f"user{index}"},
                "account2": {"username": f"user{index}.old"},
            }
            for index in range(1, 13)
        ]

    monkeypatch.setattr(
        remediation_action_tools,
        "list_remediation_items",
        fake_list_remediation_items,
    )

    result = RudrixRemediationOperationsTool().execute(
        db=object(),
        arguments={"limit": 10},
    )

    assert result["totalMatching"] == 12
    assert result["returnedItems"] == 10
    assert result["count"] == 10
    assert len(result["items"]) == 10


def test_all_scope_keeps_non_actionable_states(monkeypatch):
    from app.ai.tools import remediation_action_tools

    def fake_list_remediation_items(db, **kwargs):
        del db, kwargs
        return [
            {
                "id": 1,
                "application": "ServiceNow",
                "status": "IGNORED",
                "account1Key": "sn:1",
                "account2Key": "sn:2",
            },
            {
                "id": 2,
                "application": "ServiceNow",
                "status": "ACTIONED",
                "account1Key": "sn:3",
                "account2Key": "sn:4",
            },
        ]

    monkeypatch.setattr(
        remediation_action_tools,
        "list_remediation_items",
        fake_list_remediation_items,
    )

    result = RudrixRemediationOperationsTool().execute(
        db=object(),
        arguments={"status": "ALL", "limit": 10},
    )

    assert result["statusScope"] == "ALL"
    assert result["totalMatching"] == 2
    assert [item["status"] for item in result["items"]] == ["IGNORED", "ACTIONED"]
