from unittest.mock import Mock, patch

from app.ai.agent_core import AgentState, reduce_tool_result, render_state_for_planner
from app.ai.agent_core.capability_retriever import CapabilityRetriever
from app.ai.agent_core.forced_grounding import force_grounding_tool_calls
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.operations_tools import GetExecutionDetailsTool
from app.schemas.chat import ChatResponse, ToolInvocationResponse


def _run_state() -> AgentState:
    return reduce_tool_result(
        AgentState(),
        tool_name="run_integration",
        tool_result={
            "success": True,
            "data": {
                "started": True,
                "integration": {
                    "id": 12,
                    "name": "Active Directory",
                    "connectorType": "LOCAL",
                },
                "aggregationType": "FULL",
                "execution": {
                    "executionId": 91,
                    "integrationId": 12,
                    "status": "COMPLETED",
                    "aggregationType": "FULL",
                    "accountsScanned": 1450,
                    "accountsCreated": 20,
                    "accountsUpdated": 15,
                    "accountsUnchanged": 1415,
                    "accountsDeleted": 0,
                    "duplicateGroups": 7,
                    "duplicateAccounts": 15,
                    "errorMessage": None,
                    "completedAt": "2026-10-16T14:30:00+05:30",
                },
            },
        },
    )


def _definition(name: str) -> dict:
    return next(
        item for item in create_ai_tool_registry().definitions()
        if item.get("name") == name
    )


def test_run_integration_persists_source_and_execution_for_followups():
    state = _run_state()

    assert state.current_integration is not None
    assert state.current_integration.id == 12
    assert state.current_integration.label == "Active Directory"
    assert state.current_integration.attributes["integration"] == "Active Directory"

    assert state.current_execution is not None
    assert state.current_execution.id == 91
    assert state.current_execution.label == "COMPLETED"
    assert state.current_execution.attributes["execution_id"] == 91
    assert state.current_execution.attributes["accountsScanned"] == 1450
    assert state.current_execution.attributes["duplicateGroups"] == 7


def test_execution_details_is_retrieved_for_status_followup():
    state = _run_state()
    definitions = create_ai_tool_registry().definitions()
    retriever = CapabilityRetriever(definitions)

    selected = retriever.select(
        "Did it complete?\n" + render_state_for_planner(state),
        limit=10,
        always_include=set(),
    )
    names = {str(item.get("name") or "") for item in selected}

    assert "get_execution_details" in names


def test_did_it_complete_reuses_grounded_execution_id_without_model_guess():
    provider = Mock()
    state = _run_state()

    calls = force_grounding_tool_calls(
        provider=provider,
        model="llama3.1:8b",
        user_message="Did it complete?",
        grounded_state=render_state_for_planner(state),
        definitions=[_definition("get_execution_details")],
    )

    provider.chat.assert_not_called()
    assert len(calls) == 1
    assert calls[0].name == "get_execution_details"
    assert calls[0].arguments == {"execution_id": 91}


def test_referential_status_prefers_exact_execution_over_latest_filter():
    provider = Mock()
    state = _run_state()

    calls = force_grounding_tool_calls(
        provider=provider,
        model="llama3.1:8b",
        user_message="Did it complete?",
        grounded_state=render_state_for_planner(state),
        definitions=[
            _definition("get_latest_execution"),
            _definition("get_execution_details"),
        ],
    )

    provider.chat.assert_not_called()
    assert len(calls) == 1
    assert calls[0].name == "get_execution_details"
    assert calls[0].arguments == {"execution_id": 91}


def test_result_followup_reuses_grounded_execution_id_without_model_guess():
    provider = Mock()
    state = _run_state()

    calls = force_grounding_tool_calls(
        provider=provider,
        model="llama3.1:8b",
        user_message="What was the result?",
        grounded_state=render_state_for_planner(state),
        definitions=[_definition("get_execution_details")],
    )

    provider.chat.assert_not_called()
    assert len(calls) == 1
    assert calls[0].arguments == {"execution_id": 91}


def test_scanned_count_followup_reuses_grounded_execution_id_without_model_guess():
    provider = Mock()
    state = _run_state()

    calls = force_grounding_tool_calls(
        provider=provider,
        model="llama3.1:8b",
        user_message="How many accounts were scanned?",
        grounded_state=render_state_for_planner(state),
        definitions=[_definition("get_execution_details")],
    )

    provider.chat.assert_not_called()
    assert len(calls) == 1
    assert calls[0].arguments == {"execution_id": 91}


def test_execution_details_returns_authoritative_persisted_summary():
    persisted = {
        "executionId": 91,
        "integrationId": 12,
        "integrationName": "Active Directory",
        "connectorType": "LOCAL",
        "status": "COMPLETED",
        "aggregationType": "FULL",
        "accountsScanned": 1450,
        "accountsCreated": 20,
        "accountsUpdated": 15,
        "accountsUnchanged": 1415,
        "accountsDeleted": 0,
        "duplicateGroups": 7,
        "duplicateAccounts": 15,
        "errorMessage": None,
        "completedAt": "2026-10-16T14:30:00+05:30",
    }

    with patch(
        "app.ai.tools.operations_tools.get_operation",
        return_value=persisted,
    ):
        result = GetExecutionDetailsTool().execute(
            db=Mock(),
            arguments={"execution_id": 91},
        )

    assert result["found"] is True
    assert result["resultType"] == "integration_execution"
    assert result["execution"] == persisted
    assert "Active Directory full aggregation (execution 91) is COMPLETED." in result["message"]
    assert "Accounts scanned: 1450." in result["message"]
    assert "groups: 7, accounts: 15" in result["message"]


def test_execution_result_overrides_generic_model_prose():
    authoritative = (
        "Active Directory full aggregation (execution 91) is COMPLETED. "
        "Accounts scanned: 1450. Duplicates — groups: 7, accounts: 15."
    )

    response = ChatResponse(
        conversationId="aggregation-followup",
        message="I'm Rudrix. What would you like to accomplish?",
        model="llama3.1:8b",
        toolsUsed=[
            ToolInvocationResponse(
                name="get_execution_details",
                arguments={"execution_id": 91},
                result={
                    "success": True,
                    "data": {
                        "found": True,
                        "resultType": "integration_execution",
                        "execution": {"executionId": 91, "status": "COMPLETED"},
                        "message": authoritative,
                    },
                },
            )
        ],
        sources=[],
    )

    assert response.message == authoritative
    assert "What would you like" not in response.message


def test_failed_execution_summary_includes_real_failure_reason():
    persisted = {
        "executionId": 92,
        "integrationId": 12,
        "integrationName": "Active Directory",
        "status": "FAILED",
        "aggregationType": "FULL",
        "accountsScanned": 0,
        "accountsCreated": 0,
        "accountsUpdated": 0,
        "accountsUnchanged": 0,
        "accountsDeleted": 0,
        "duplicateGroups": 0,
        "duplicateAccounts": 0,
        "errorMessage": "Unable to connect to source.",
        "completedAt": "2026-10-16T14:35:00+05:30",
    }

    with patch(
        "app.ai.tools.operations_tools.get_operation",
        return_value=persisted,
    ):
        result = GetExecutionDetailsTool().execute(
            db=Mock(),
            arguments={"execution_id": 92},
        )

    assert "is FAILED" in result["message"]
    assert "Failure reason: Unable to connect to source." in result["message"]
