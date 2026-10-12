from __future__ import annotations

from types import SimpleNamespace

from app.ai.agent_core.models import AgentState
from app.ai.agent_core.state import reduce_tool_result
from app.ai.fast_agent_service import _state_instruction
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.orphan_tools import GroundedAccountInvestigationTool, SearchOrphanAccountsTool
from app.services.orphan_account_service import _filter_rows_by_search, list_orphan_accounts
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
                "reportFilters": {"integrationId": 12, "orphanType": "UNMATCHED_ACCOUNT"},
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
    assert state.last_filters["filters"]["orphanType"] == "UNMATCHED_ACCOUNT"


def test_grounded_orphan_report_context_is_visible_to_generic_agent():
    state = AgentState(
        last_filters={
            "context": "orphan_accounts",
            "reportType": "orphan_accounts",
            "filters": {"integrationId": 12, "orphanType": "UNMATCHED_ACCOUNT"},
        }
    )
    rendered = _state_instruction(state)

    assert "orphan_accounts" in rendered
    assert "integrationId" in rendered
    assert "UNMATCHED_ACCOUNT" in rendered


def test_orphan_report_extension_is_available_to_shared_report_system():
    register_orphan_report()

    catalog_item = next(item for item in REPORT_CATALOG if item["type"] == ORPHAN_REPORT_TYPE)
    assert "orphanType" in catalog_item["filters"]
    assert "status" in catalog_item["filters"]
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


def _orphan_row(display_name: str, employee_id: str, username: str):
    orphan = SimpleNamespace(
        evidence={
            "reason": "No configured correlation rule matched an authoritative identity.",
            "correlationAttempts": [],
        },
        orphan_type="UNMATCHED_ACCOUNT",
        status="OPEN",
        correlation_method="CORRELATION_POLICY",
    )
    account = SimpleNamespace(
        native_identity=username,
        username=username,
        email=None,
        employee_id=employee_id,
        display_name=display_name,
        application="Active Directory",
    )
    integration = SimpleNamespace(name="Active Directory", connector_type="LOCAL")
    return orphan, account, integration


def test_natural_language_orphan_followup_resolves_named_account():
    rows = [
        _orphan_row("Pooja Mehta", "W90009", "pmehta"),
        _orphan_row("Rudra Reddy", "W90010", "rreddy"),
        _orphan_row("David Miller", "W90015", "dmiller"),
    ]

    matches = _filter_rows_by_search(rows, "why is Pooja Mehta orphaned?")

    assert len(matches) == 1
    assert matches[0][1].display_name == "Pooja Mehta"


def test_natural_language_orphan_followup_resolves_employee_id():
    rows = [
        _orphan_row("Pooja Mehta", "W90009", "pmehta"),
        _orphan_row("Rudra Reddy", "W90010", "rreddy"),
    ]

    matches = _filter_rows_by_search(rows, "why did correlation fail for W90009?")

    assert len(matches) == 1
    assert matches[0][1].employee_id == "W90009"


def test_broad_orphan_sentence_keeps_source_filtered_rows():
    rows = [
        _orphan_row("Pooja Mehta", "W90009", "pmehta"),
        _orphan_row("Rudra Reddy", "W90010", "rreddy"),
    ]

    matches = _filter_rows_by_search(rows, "show current orphan accounts from Active Directory")

    assert matches == rows


def test_investigation_tool_keeps_named_orphan_sentence_searchable(monkeypatch):
    captured = {}

    def fake_list_orphans(_db, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        "app.ai.tools.orphan_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    GroundedAccountInvestigationTool().execute(
        db=object(),
        arguments={
            "query": "why is Pooja Mehta orphaned?",
            "orphan_only": True,
        },
    )

    assert captured["search"] == "why is Pooja Mehta orphaned?"


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


def test_known_orphan_type_sent_as_status_is_not_applied_to_workflow_status():
    db = _CaptureDb()
    result = list_orphan_accounts(
        db,
        integration_name="Active Directory",
        status="UNMATCHED_ACCOUNT",
    )

    assert result == []
    where_sql = str(db.statement).partition("WHERE")[2].lower()
    assert "orphan_states.orphan_type" in where_sql
    assert "orphan_states.status =" not in where_sql


def test_orphan_tool_recovers_model_status_field_mixup(monkeypatch):
    captured = {}

    def fake_list_orphans(_db, **kwargs):
        captured.update(kwargs)
        return [
            {
                "integrationId": 12,
                "integrationName": "Active Directory",
                "application": "Active Directory",
                "sourceAccountId": 1,
                "displayName": "Pooja Mehta",
                "orphanType": "UNMATCHED_ACCOUNT",
                "orphanStatus": None,
            }
        ]

    monkeypatch.setattr(
        "app.ai.tools.orphan_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    result = SearchOrphanAccountsTool().execute(
        db=object(),
        arguments={
            "integration": "Active Directory",
            "status": "UNMATCHED_ACCOUNT",
        },
    )

    assert result["count"] == 1
    assert captured["orphan_type"] == "UNMATCHED_ACCOUNT"
    assert captured["status"] is None
    assert result["reportFilters"]["orphanType"] == "UNMATCHED_ACCOUNT"
    assert "status" not in result["reportFilters"]
