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


def test_duplicate_lookup_keeps_duplicate_search_in_generic_capability_surface():
    request = ChatRequest(
        message="is W00003 a duplicate?",
        history=[],
    )

    selected = _select_definitions(_definitions(), request)
    names = {item["name"] for item in selected}

    assert "search_duplicate_groups" in names
    assert names == {item["name"] for item in _definitions()}


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

    assert "Aditya Sinha" in message
    assert "asinha.legacy" in message
    assert "candidate ID 701" in message
    assert "96% confidence" in message
    assert "Based on" not in message
    assert "tool" not in message.lower()


def test_account_formatter_does_not_render_null_status_or_meta_commentary():
    message = format_account_investigation(
        {
            "items": [
                {
                    "sourceAccountId": 203,
                    "application": "Active Directory",
                    "username": "asinha",
                    "displayName": "Aditya Sinha",
                    "email": "asinha@examplecorp.com",
                    "employeeId": "W00003",
                    "nativeIdentity": "02ebc443-12b6-5a1e-bbca-073c9b0f7879",
                    "accountStatus": None,
                    "orphaned": False,
                }
            ]
        }
    )

    assert "Aditya Sinha" in message
    assert "Status: null" not in message
    assert "Based on" not in message
    assert "tool call" not in message.lower()
