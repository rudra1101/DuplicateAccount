from app.ai.agent_core import (
    AgentState,
    CapabilityCatalog,
    EntityType,
    reduce_tool_result,
)
from app.ai.tools import create_ai_tool_registry


def test_capability_catalog_is_generated_from_real_tool_registry():
    catalog = CapabilityCatalog(create_ai_tool_registry())
    capabilities = {item.name: item for item in catalog.capabilities()}

    assert "investigate_accounts" in capabilities
    assert capabilities["investigate_accounts"].domain == "account"
    assert capabilities["investigate_accounts"].fast_path is True

    assert "search_duplicate_groups" in capabilities
    assert capabilities["search_duplicate_groups"].domain == "duplicate"

    assert "generate_report" in capabilities
    assert capabilities["generate_report"].kind.value == "WRITE"

    assert "search_knowledge_base" in capabilities
    assert capabilities["search_knowledge_base"].kind.value == "KNOWLEDGE"


def test_account_tool_result_establishes_structured_account_context():
    state = reduce_tool_result(
        AgentState(),
        tool_name="investigate_accounts",
        tool_result={
            "success": True,
            "data": {
                "count": 1,
                "items": [
                    {
                        "sourceAccountId": 203,
                        "integrationId": 12,
                        "integrationName": "Active Directory",
                        "application": "Active Directory",
                        "nativeIdentity": "abc-123",
                        "username": "asinha.legacy",
                        "displayName": "Aditya Sinha",
                        "email": "asinha@examplecorp.com",
                        "employeeId": "W00003",
                        "orphaned": False,
                    }
                ],
            },
        },
    )

    assert state.current_account is not None
    assert state.current_account.entity_type == EntityType.SOURCE_ACCOUNT
    assert state.current_account.id == 203
    assert state.current_account.attributes["employeeId"] == "W00003"
    assert state.current_integration is not None
    assert state.current_integration.id == 12


def test_duplicate_result_establishes_group_and_single_candidate_context():
    state = reduce_tool_result(
        AgentState(),
        tool_name="search_duplicate_groups",
        tool_result={
            "success": True,
            "data": {
                "groups": [
                    {
                        "groupId": 2477,
                        "application": "Active Directory",
                        "primaryUsername": "asinha.legacy",
                        "duplicateCount": 1,
                        "highestConfidence": 97,
                        "primaryAccount": {
                            "sourceAccountId": 203,
                            "username": "asinha.legacy",
                            "displayName": "Aditya Sinha",
                            "employeeId": "W00003",
                        },
                        "candidates": [
                            {
                                "id": 9694,
                                "username": "asinha",
                                "confidence": 97,
                            }
                        ],
                    }
                ]
            },
        },
    )

    assert state.current_duplicate_group is not None
    assert state.current_duplicate_group.id == 2477
    assert state.current_duplicate_candidate is not None
    assert state.current_duplicate_candidate.id == 9694
    assert state.current_duplicate_candidate.attributes["groupId"] == 2477
    assert state.current_account is not None
    assert state.current_account.attributes["employeeId"] == "W00003"


def test_failed_tool_result_never_mutates_agent_state():
    original = AgentState()
    updated = reduce_tool_result(
        original,
        tool_name="search_duplicate_groups",
        tool_result={"success": False, "error": "boom"},
    )

    assert updated == original
