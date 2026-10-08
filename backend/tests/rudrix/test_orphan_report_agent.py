from __future__ import annotations

from app.ai.agent_core.grounded_actions import resolve_grounded_action
from app.ai.agent_core.models import AgentState
from app.ai.agent_core.state import reduce_tool_result
from app.ai.tools import create_ai_tool_registry
from app.services.orphan_report_extension import ORPHAN_REPORT_TYPE, register_orphan_report
from app.services.report_service import REPORT_CATALOG, ROW_BUILDERS


def test_orphan_capability_is_registered_and_query_is_optional():
    registry = create_ai_tool_registry()
    definitions = {item["name"]: item for item in registry.definitions()}

    assert "search_orphan_accounts" in definitions
    assert "investigate_accounts" in definitions
    assert definitions["investigate_accounts"]["parameters"].get("required") == []


def test_orphan_search_result_persists_report_filters_and_full_evidence():
    state = reduce_tool_result(
        AgentState(),
        tool_name="investigate_accounts",
        tool_result={
            "success": True,
            "data": {
                "queryMode": "orphan_search",
                "reportType": "orphan_accounts",
                "reportFilters": {"integrationId": 12, "status": "UNMATCHED_ACCOUNT"},
                "items": [
                    {
                        "sourceAccountId": 203,
                        "integrationId": 12,
                        "integrationName": "Active Directory",
                        "application": "Active Directory",
                        "username": "asinha",
                        "displayName": "Aditya Sinha",
                        "employeeId": "W00003",
                        "orphaned": True,
                        "orphanType": "UNMATCHED_ACCOUNT",
                        "reason": "NO_MATCH",
                        "correlationAttempts": [
                            {"attribute": "employeeID", "matched": False}
                        ],
                    }
                ],
            },
        },
    )

    assert state.current_account is not None
    assert state.current_account.id == 203
    assert state.current_account.attributes["reason"] == "NO_MATCH"
    assert state.current_account.attributes["correlationAttempts"]
    assert state.current_integration is not None
    assert state.current_integration.id == 12
    assert state.last_filters["reportType"] == "orphan_accounts"
    assert state.last_filters["filters"]["integrationId"] == 12


def test_generate_report_for_these_uses_grounded_orphan_filters():
    state = AgentState(
        last_filters={
            "context": "orphan_accounts",
            "reportType": "orphan_accounts",
            "filters": {"integrationId": 12, "status": "UNMATCHED_ACCOUNT"},
        }
    )

    action = resolve_grounded_action("generate a report for these", state)

    assert action is not None
    assert action.tool_name == "generate_report"
    assert action.arguments == {
        "report_type": "orphan_accounts",
        "filters": {"integrationId": 12, "status": "UNMATCHED_ACCOUNT"},
    }


def test_report_date_refinement_keeps_existing_filters():
    state = AgentState(
        last_filters={
            "context": "orphan_accounts",
            "reportType": "orphan_accounts",
            "filters": {"integrationId": 12},
        }
    )

    action = resolve_grounded_action("only include accounts from the last 30 days", state)

    assert action is not None
    assert action.tool_name == "generate_report"
    filters = action.arguments["filters"]
    assert filters["integrationId"] == 12
    assert isinstance(filters["dateFrom"], str)


def test_orphan_report_extension_is_available_to_shared_report_system():
    register_orphan_report()

    assert any(item["type"] == ORPHAN_REPORT_TYPE for item in REPORT_CATALOG)
    assert ORPHAN_REPORT_TYPE in ROW_BUILDERS
