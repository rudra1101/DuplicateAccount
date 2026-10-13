from __future__ import annotations

from app.ai.agent_core.models import AgentState
from app.ai.agent_core.state import reduce_tool_result
from app.ai.fast_agent_service import _authoritative_investigation_message
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.orphan_explanation_tools import ExplainOrphanAccountTool
from app.ai.tools.registry import TOOL_PERMISSION_MAP
from app.schemas.chat import ChatResponse, ToolInvocationResponse


def _neha_orphan() -> dict:
    return {
        "orphanStateId": 501,
        "sourceAccountId": 108,
        "integrationId": 12,
        "integrationName": "Active Directory",
        "connectorType": "LOCAL",
        "application": "Active Directory",
        "nativeIdentity": "nverma",
        "username": "nverma",
        "displayName": "Neha Verma",
        "email": "neha.verma@example.com",
        "employeeId": "W90008",
        "accountStatus": "ACTIVE",
        "orphaned": True,
        "orphanType": "UNMATCHED_ACCOUNT",
        "orphanStatus": "OPEN",
        "correlationMethod": None,
        "reason": "No configured correlation rule matched an authoritative identity.",
        "policyId": 7,
        "policyName": "AD to HR",
        "strategy": "FIRST_MATCH_WINS",
        "correlationAttempts": [
            {
                "priority": 1,
                "accountAttribute": "employeeId",
                "identityAttribute": "employeeId",
                "matchType": "EXACT",
                "accountValue": "W90008",
                "matches": 0,
                "matchedIdentities": [],
                "result": "NO_MATCH",
            },
            {
                "priority": 2,
                "accountAttribute": "email",
                "identityAttribute": "email",
                "matchType": "CASE_INSENSITIVE",
                "accountValue": "neha.verma@example.com",
                "matches": 0,
                "matchedIdentities": [],
                "result": "NO_MATCH",
            },
        ],
        "matchedIdentity": None,
    }


def _explanation_result(account: dict | None = None) -> dict:
    account = account or _neha_orphan()
    message = (
        "**Neha Verma** (employee ID W90008, account nverma) is currently classified "
        "as **UNMATCHED_ACCOUNT**."
    )
    return {
        "success": True,
        "data": {
            "resultType": "orphan_explanation",
            "found": True,
            "account": account,
            "explanation": {
                "reason": account.get("reason"),
                "orphanType": account.get("orphanType"),
                "correlationAttempts": account.get("correlationAttempts"),
                "matchedIdentity": account.get("matchedIdentity"),
            },
            "reportType": "orphan_accounts",
            "reportFilters": {"integrationId": 12, "search": "W90008"},
            "message": message,
        },
    }


def test_orphan_explanation_capability_is_registered_and_authorized():
    registry = create_ai_tool_registry()
    definitions = {definition["name"]: definition for definition in registry.definitions()}

    assert "explain_orphan_account" in definitions
    assert TOOL_PERMISSION_MAP["explain_orphan_account"] == "integration.view"
    assert definitions["explain_orphan_account"]["parameters"]["required"] == []


def test_named_orphan_explanation_returns_rule_level_grounded_evidence(monkeypatch):
    captured = {}

    def fake_list_orphans(_db, **kwargs):
        captured.update(kwargs)
        return [_neha_orphan()]

    monkeypatch.setattr(
        "app.ai.tools.orphan_explanation_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    result = ExplainOrphanAccountTool().execute(
        db=object(),
        arguments={"reference": "why is Neha Verma orphaned?"},
    )

    assert result["found"] is True
    assert result["resultType"] == "orphan_explanation"
    assert result["account"]["sourceAccountId"] == 108
    assert captured["search"] == "why is Neha Verma orphaned?"
    assert captured["source_account_id"] is None
    assert "Neha Verma" in result["message"]
    assert "W90008" in result["message"]
    assert "AD to HR" in result["message"]
    assert "`employeeId`" in result["message"]
    assert "**NO_MATCH**" in result["message"]
    assert "matched 0 authoritative identities" in result["message"]
    assert "No authoritative identity was matched" in result["message"]
    assert result["reportFilters"] == {"integrationId": 12, "search": "W90008"}


def test_grounded_source_account_id_bypasses_fuzzy_reference_lookup(monkeypatch):
    captured = {}

    def fake_list_orphans(_db, **kwargs):
        captured.update(kwargs)
        return [_neha_orphan()]

    monkeypatch.setattr(
        "app.ai.tools.orphan_explanation_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    result = ExplainOrphanAccountTool().execute(
        db=object(),
        arguments={"source_account_id": 108},
    )

    assert result["found"] is True
    assert captured["source_account_id"] == 108
    assert captured["search"] is None


def test_ambiguous_explanation_lists_only_persisted_matched_identities(monkeypatch):
    account = _neha_orphan()
    account.update(
        {
            "orphanType": "AMBIGUOUS_CORRELATION",
            "reason": "Correlation rule matched multiple authoritative identities.",
            "correlationAttempts": [
                {
                    "priority": 1,
                    "accountAttribute": "employeeId",
                    "identityAttribute": "employeeId",
                    "matchType": "EXACT",
                    "accountValue": "W90008",
                    "matches": 2,
                    "result": "AMBIGUOUS",
                    "matchedIdentities": [
                        {
                            "id": 201,
                            "sourceIdentityId": "HR-201",
                            "displayName": "Neha Verma",
                            "username": "neha.hr",
                            "email": "neha.hr@example.com",
                            "employeeId": "W90008",
                            "employmentStatus": "ACTIVE",
                        },
                        {
                            "id": 202,
                            "sourceIdentityId": "HR-202",
                            "displayName": "Neha V.",
                            "username": "neha.v2",
                            "email": "neha.v2@example.com",
                            "employeeId": "W90008",
                            "employmentStatus": "ACTIVE",
                        },
                    ],
                }
            ],
        }
    )

    monkeypatch.setattr(
        "app.ai.tools.orphan_explanation_tools.list_orphan_accounts",
        lambda _db, **_kwargs: [account],
    )

    result = ExplainOrphanAccountTool().execute(
        db=object(),
        arguments={"reference": "Neha Verma"},
    )

    assert "**AMBIGUOUS**" in result["message"]
    assert "matched 2 authoritative identities" in result["message"]
    assert "neha.hr" in result["message"]
    assert "neha.v2" in result["message"]
    assert len(result["explanation"]["matchedIdentities"]) == 2


def test_explanation_result_updates_account_integration_and_real_matched_identity():
    account = _neha_orphan()
    account["orphanType"] = "TERMINATED_IDENTITY"
    account["matchedIdentity"] = {
        "id": 301,
        "sourceIdentityId": "HR-301",
        "displayName": "Neha Verma",
        "username": "neha.hr",
        "email": "neha.hr@example.com",
        "employeeId": "W90008",
        "employmentStatus": "TERMINATED",
    }

    updated = reduce_tool_result(
        AgentState(),
        tool_name="explain_orphan_account",
        tool_result=_explanation_result(account),
    )

    assert updated.current_account is not None
    assert updated.current_account.id == 108
    assert updated.current_integration is not None
    assert updated.current_integration.id == 12
    assert updated.current_identity is not None
    assert updated.current_identity.id == 301
    assert updated.current_identity.attributes["employmentStatus"] == "TERMINATED"


def test_explanation_drilldown_preserves_broader_orphan_collection_scope():
    initial = AgentState(
        last_filters={
            "context": "orphan_accounts",
            "reportType": "orphan_accounts",
            "filters": {"integrationId": 12},
            "resultCount": 19,
        }
    )

    updated = reduce_tool_result(
        initial,
        tool_name="explain_orphan_account",
        tool_result=_explanation_result(),
    )

    assert updated.last_filters["resultCount"] == 19
    assert updated.last_filters["filters"] == {"integrationId": 12}
    assert updated.current_account is not None
    assert updated.current_account.label == "Neha Verma"


def test_authoritative_chat_response_keeps_server_generated_orphan_explanation():
    result = _explanation_result()
    message = result["data"]["message"]
    invocation = ToolInvocationResponse(
        name="explain_orphan_account",
        arguments={"reference": "Neha Verma"},
        result=result,
    )

    response = ChatResponse(
        conversationId="conversation-orphan-explain",
        message="I do not have enough context to explain why this account is orphaned.",
        model="llama3.1:8b",
        toolsUsed=[invocation],
        sources=[],
    )

    assert response.message == message
    assert _authoritative_investigation_message([invocation]) == message
