from __future__ import annotations

from app.ai.agent_core.models import AgentState
from app.ai.agent_core.state import reduce_tool_result
from app.ai.fast_agent_service import _state_instruction
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.orphan_tools import SearchOrphanAccountsTool
from app.services.orphan_account_service import list_orphan_accounts
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


def test_grounded_orphan_report_context_is_visible_to_generic_agent():
    state = AgentState(
        last_filters={
            "context": "orphan_accounts",
            "reportType": "orphan_accounts",
            "filters": {"integrationId": 12, "status": "UNMATCHED_ACCOUNT"},
        }
    )
    rendered = _state_instruction(state)

    assert "orphan_accounts" in rendered
    assert "integrationId" in rendered
    assert "UNMATCHED_ACCOUNT" in rendered


def test_orphan_report_extension_is_available_to_shared_report_system():
    register_orphan_report()

    assert any(item["type"] == ORPHAN_REPORT_TYPE for item in REPORT_CATALOG)
    assert ORPHAN_REPORT_TYPE in ROW_BUILDERS


class _CaptureDb:
    def __init__(self):
        self.statement = None

    class _Result:
        def all(self):
            return []

    def execute(self, statement):
        self.statement = statement
        return self._Result()


def test_orphan_service_matches_ui_current_state_semantics():
    db = _CaptureDb()
    result = list_orphan_accounts(db, integration_id=12)

    assert result == []
    sql = str(db.statement)
    where_sql = sql.partition("WHERE")[2]
    assert "orphan_states.active" in where_sql
    assert "source_accounts.active" not in where_sql


def test_human_source_reference_matches_name_connector_or_application():
    db = _CaptureDb()
    result = list_orphan_accounts(db, integration_name="Active Directory")

    assert result == []
    sql = str(db.statement)
    where_sql = sql.partition("WHERE")[2].lower()
    assert "integrations.name" in where_sql
    assert "integrations.connector_type" in where_sql
    assert "source_accounts.application" in where_sql
    assert " or " in where_sql


def test_duplicate_human_source_fields_do_not_overconstrain_orphan_search(monkeypatch):
    captured = {}

    def fake_list_orphans(_db, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        "app.ai.tools.orphan_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    result = SearchOrphanAccountsTool().execute(
        db=object(),
        arguments={
            "integration": "Active Directory",
            "application": "active_directory",
        },
    )

    assert result["count"] == 0
    assert captured["integration_name"] == "Active Directory"
    assert captured["application"] is None
