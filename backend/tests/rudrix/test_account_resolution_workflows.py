from app.ai.tools import create_ai_tool_registry
from app.ai.tools.account_resolution_tools import (
    GroundedCreateRemediationTicketTool,
    GroundedDuplicateGroupDetailsTool,
    GroundedReviewOperationsTool,
    GroundedSearchDuplicateGroupsTool,
    _candidate_matches_reference,
    _normalize_duplicate_search,
    _optional_scope,
)


def test_registry_uses_grounded_duplicate_and_ticket_tools():
    registry = create_ai_tool_registry()

    assert isinstance(
        registry.get("search_duplicate_groups"),
        GroundedSearchDuplicateGroupsTool,
    )
    assert isinstance(
        registry.get("get_duplicate_group_details"),
        GroundedDuplicateGroupDetailsTool,
    )
    assert isinstance(
        registry.get("get_review_statistics"),
        GroundedReviewOperationsTool,
    )
    assert isinstance(
        registry.get("create_remediation_ticket"),
        GroundedCreateRemediationTicketTool,
    )


def test_duplicate_search_extracts_employee_id_from_full_question():
    assert _normalize_duplicate_search("is W00003 is a duplicate?") == "W00003"
    assert _normalize_duplicate_search("Is W00003 a duplicate account?") == "W00003"
    assert _normalize_duplicate_search("show duplicates for Aditya Sinha") == "Aditya Sinha"


def test_duplicate_scope_ignores_model_null_placeholders():
    assert _optional_scope(None) is None
    assert _optional_scope("null") is None
    assert _optional_scope("the null application") is None
    assert _optional_scope("integration is unspecified") is None
    assert _optional_scope("Active Directory") == "Active Directory"


def test_candidate_reference_matches_employee_id_and_username():
    candidate = {
        "username": "asinha.legacy",
        "account": {
            "employeeId": "W00003",
            "email": "legacy@examplecorp.com",
        },
    }

    assert _candidate_matches_reference(candidate, "W00003") is True
    assert _candidate_matches_reference(candidate, "asinha.legacy") is True
    assert _candidate_matches_reference(candidate, "W99999") is False


def test_group_details_treats_employee_id_as_reference(monkeypatch):
    captured = {}

    def fake_search(self, *, db, arguments):
        del self, db
        captured.update(arguments)
        return {"found": True, "groups": []}

    monkeypatch.setattr(
        GroundedSearchDuplicateGroupsTool,
        "execute",
        fake_search,
    )

    result = GroundedDuplicateGroupDetailsTool().execute(
        db=object(),
        arguments={"group_id": "W00003"},
    )

    assert result["found"] is True
    assert captured["search"] == "W00003"
    assert captured["minimum_confidence"] == 0


def test_review_stats_with_employee_id_rechecks_duplicate_data(monkeypatch):
    captured = {}

    def fake_reference_search(self, *, db, arguments, reference):
        del self, db
        captured["reference"] = reference
        captured["arguments"] = arguments
        return {"found": True, "totalMatchingGroups": 1, "groups": []}

    monkeypatch.setattr(
        GroundedReviewOperationsTool,
        "_search_reference",
        fake_reference_search,
    )

    result = GroundedReviewOperationsTool().execute(
        db=object(),
        arguments={
            "operation": "STATS",
            "candidate_id": "W00003",
            "account_reference": None,
            "integration": "the null integration",
            "application": "application is unspecified",
        },
    )

    assert result["found"] is True
    assert captured["reference"] == "W00003"


def test_confirm_by_primary_reference_requires_selection_when_multiple_candidates(monkeypatch):
    def fake_reference_search(self, *, db, arguments, reference):
        del self, db, arguments
        assert reference == "W00003"
        return {
            "found": True,
            "groups": [
                {
                    "groupId": 55,
                    "application": "Active Directory",
                    "primaryUsername": "asinha",
                    "candidates": [
                        {"id": 701, "username": "asinha.legacy", "account": {}},
                        {"id": 702, "username": "asinha123", "account": {}},
                    ],
                }
            ],
        }

    monkeypatch.setattr(
        GroundedReviewOperationsTool,
        "_search_reference",
        fake_reference_search,
    )

    result = GroundedReviewOperationsTool().execute(
        db=object(),
        arguments={
            "operation": "DECIDE",
            "candidate_id": "W00003",
            "account_reference": None,
            "decision": "DUPLICATE",
            "integration": None,
            "application": None,
            "comment": None,
        },
    )

    assert result["changed"] is False
    assert result["requiresSelection"] is True
    assert result["count"] == 2
    assert {item["id"] for item in result["candidates"]} == {701, 702}


def test_ticket_tool_does_not_force_internal_id_or_action_fields():
    assert GroundedCreateRemediationTicketTool.parameters["required"] == []


def test_ticket_by_employee_id_resolves_item_but_requires_target_and_action(monkeypatch):
    def fake_items(db, status=None, application=None, min_confidence=None):
        del db, application, min_confidence
        assert status == "PENDING_ACTION"
        return [
            {
                "id": 203,
                "application": "Active Directory",
                "confidence": 96,
                "account1Key": "asinha",
                "account2Key": "asinha.legacy",
                "account1": {
                    "username": "asinha",
                    "employeeId": "W00003",
                    "email": "asinha@examplecorp.com",
                },
                "account2": {
                    "username": "asinha.legacy",
                    "employeeId": "W00003",
                    "email": "legacy@examplecorp.com",
                },
            }
        ]

    monkeypatch.setattr(
        "app.ai.tools.account_resolution_tools.list_remediation_items",
        fake_items,
    )

    result = GroundedCreateRemediationTicketTool().execute(
        db=object(),
        arguments={
            "remediation_item_id": "W00003",
            "account_reference": None,
            "target": None,
            "action": None,
        },
    )

    assert result["created"] is False
    assert result["requiresInput"] is True
    assert result["remediationItemId"] == 203
    assert result["account1"]["username"] == "asinha"
    assert result["account2"]["username"] == "asinha.legacy"


def test_ticket_lookup_does_not_invent_remediation_item(monkeypatch):
    monkeypatch.setattr(
        "app.ai.tools.account_resolution_tools.list_remediation_items",
        lambda db, status=None, application=None, min_confidence=None: [],
    )

    result = GroundedCreateRemediationTicketTool().execute(
        db=object(),
        arguments={
            "remediation_item_id": "W00003",
            "account_reference": None,
            "target": None,
            "action": None,
        },
    )

    assert result["created"] is False
    assert result["found"] is False
    assert result["reference"] == "W00003"
