from app.ai.fast_agent_service import _select_definitions
from app.ai.grounded_response_formatter import (
    format_account_investigation,
    format_duplicate_search,
)
from app.schemas.chat import ChatRequest


def _definitions():
    return [
        {"name": "investigate_accounts"},
        {"name": "search_duplicate_groups"},
        {"name": "get_duplicate_group_details"},
        {"name": "get_review_statistics"},
        {"name": "get_confidence_breakdown"},
        {"name": "get_dashboard_summary"},
    ]


def test_explicit_duplicate_lookup_routes_only_to_duplicate_search():
    request = ChatRequest(
        message="is W00003 a duplicate?",
        history=[],
    )

    selected = _select_definitions(_definitions(), request)

    assert [item["name"] for item in selected] == ["search_duplicate_groups"]


def test_duplicate_review_action_is_not_reduced_to_read_only_search():
    request = ChatRequest(
        message="confirm the duplicate for employee number W00003",
        history=[],
    )

    selected = _select_definitions(_definitions(), request)
    names = {item["name"] for item in selected}

    assert "search_duplicate_groups" in names
    assert "get_review_statistics" in names


def test_duplicate_formatter_returns_only_persisted_candidate_facts():
    message = format_duplicate_search(
        {
            "totalMatchingGroups": 1,
            "groups": [
                {
                    "groupId": 55,
                    "application": "Active Directory",
                    "primaryUsername": "asinha",
                    "highestConfidence": 96,
                    "primaryAccount": {
                        "displayName": "Aditya Sinha",
                        "username": "asinha",
                        "employeeId": "W00003",
                    },
                    "candidates": [
                        {
                            "id": 701,
                            "username": "asinha.legacy",
                            "confidence": 96,
                            "reviewDecision": None,
                        }
                    ],
                }
            ],
        }
    )

    assert "Aditya Sinha has current duplicate candidate(s)" in message
    assert "asinha.legacy" in message
    assert "candidate ID 701" in message
    assert "96% confidence" in message
    assert "Based on the tool call" not in message
    assert "original user question" not in message


def test_account_formatter_does_not_render_null_status_or_meta_commentary():
    message = format_account_investigation(
        {
            "count": 1,
            "items": [
                {
                    "displayName": "Aditya Sinha",
                    "application": "Active Directory",
                    "username": "asinha",
                    "email": "asinha@examplecorp.com",
                    "employeeId": "W00003",
                    "accountStatus": "null",
                    "orphaned": False,
                }
            ],
        }
    )

    assert "Aditya Sinha" in message
    assert "Employee ID: W00003" in message
    assert "Orphaned: No" in message
    assert "Status: null" not in message
    assert "tool call response" not in message
