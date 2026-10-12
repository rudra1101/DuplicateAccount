from __future__ import annotations

from types import SimpleNamespace

from app.ai.agent_core.capabilities import CapabilityCatalog
from app.ai.agent_core.models import AgentState, CapabilityKind
from app.ai.agent_core.state import reduce_tool_result
from app.ai.fast_agent_service import run_identity_agent_stream_fast
from app.ai.providers.base import ProviderResponse
from app.schemas.chat import ChatRequest


class _ReportFollowupProvider:
    def __init__(self) -> None:
        self.stream_calls = 0
        self.plan_calls = 0

    def stream_chat(self, *, model, messages, tools):
        self.stream_calls += 1
        names = {item.get("name") for item in tools}
        assert "generate_report" in names
        assert "search_orphan_accounts" in names

        response = ProviderResponse(
            text=(
                "I'm Rudrix, the AI copilot for IdentityAI. "
                "What would you like to accomplish?"
            ),
            assistant_message={
                "role": "assistant",
                "content": "What would you like to accomplish?",
            },
            tool_calls=[],
            model=model,
        )
        yield {"type": "result", "response": response}

    def chat(self, *, model, messages, tools):
        self.plan_calls += 1
        raise AssertionError(
            "Referential report arguments should be bound from grounded state "
            "without another model planning call."
        )


class _ReportFollowupRegistry:
    def definitions(self):
        return [
            {
                "name": "search_orphan_accounts",
                "description": "Search current orphan account records by source and filters.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "integration": {"type": ["string", "null"]},
                        "search": {"type": ["string", "null"]},
                    },
                    "required": [],
                },
            },
            {
                "name": "generate_report",
                "description": (
                    "Generate, create, export, or download a current IdentityAI report "
                    "from the user's grounded data and filters."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report_type": {
                            "type": "string",
                            "enum": ["orphan_accounts"],
                        },
                        "filters": {
                            "type": "object",
                            "properties": {
                                "integrationId": {"type": ["integer", "null"]},
                            },
                        },
                    },
                    "required": ["report_type", "filters"],
                },
            },
        ]

    def execute(self, *, name, db, arguments):
        assert name == "generate_report"
        assert arguments == {
            "report_type": "orphan_accounts",
            "filters": {"integrationId": 12},
        }
        return {
            "message": (
                "Generated **Orphan Accounts** with **19** matching row(s). "
                "[Download CSV](/api/reports/rudrix-download?reportType=orphan_accounts&integrationId=12)"
            ),
            "reportType": "orphan_accounts",
            "total": 19,
            "downloadUrl": (
                "/api/reports/rudrix-download?reportType=orphan_accounts&integrationId=12"
            ),
            "clientAction": {
                "type": "DOWNLOAD_REPORT",
                "filters": {"integrationId": 12},
            },
        }


def test_generate_report_is_safe_read_export_capability():
    catalog = CapabilityCatalog(_ReportFollowupRegistry())
    report = next(item for item in catalog.capabilities() if item.name == "generate_report")
    assert report.kind == CapabilityKind.READ


def test_referential_orphan_report_reuses_grounded_result_filters(monkeypatch):
    import app.ai.fast_agent_service as fast_agent

    provider = _ReportFollowupProvider()
    monkeypatch.setattr(
        fast_agent,
        "get_ai_settings",
        lambda: SimpleNamespace(
            fast_model="fast-model",
            reasoning_model="reasoning-model",
            max_tool_iterations=4,
        ),
    )
    monkeypatch.setattr(fast_agent.AIProviderFactory, "create", lambda settings: provider)
    monkeypatch.setattr(
        fast_agent,
        "create_ai_tool_registry",
        lambda: _ReportFollowupRegistry(),
    )

    persisted = AgentState(
        last_filters={
            "context": "orphan_accounts",
            "reportType": "orphan_accounts",
            "filters": {"integrationId": 12},
        }
    ).model_dump(exclude_none=True)

    events = list(
        run_identity_agent_stream_fast(
            db=object(),
            persisted_state=persisted,
            request=ChatRequest(
                message="generate a report for these orphan accounts"
            ),
        )
    )

    done = next(event for event in events if event["type"] == "done")
    response = done["response"]

    assert provider.plan_calls == 0
    assert [tool.name for tool in response.toolsUsed] == ["generate_report"]
    assert response.toolsUsed[0].arguments["report_type"] == "orphan_accounts"
    assert response.toolsUsed[0].arguments["filters"] == {"integrationId": 12}
    assert "Generated **Orphan Accounts** with **19** matching row(s)." in response.message
    assert "Found 19 current orphan account(s)." not in response.message


def test_single_orphan_drilldown_does_not_erase_previous_collection_scope():
    broad = reduce_tool_result(
        AgentState(),
        tool_name="search_orphan_accounts",
        tool_result={
            "success": True,
            "data": {
                "reportType": "orphan_accounts",
                "reportFilters": {"integrationId": 12},
                "items": [
                    {"sourceAccountId": index, "integrationId": 12}
                    for index in range(1, 20)
                ],
            },
        },
    )

    narrowed = reduce_tool_result(
        broad,
        tool_name="search_orphan_accounts",
        tool_result={
            "success": True,
            "data": {
                "reportType": "orphan_accounts",
                "reportFilters": {
                    "integrationId": 12,
                    "search": "Pooja Mehta",
                },
                "items": [
                    {
                        "sourceAccountId": 9,
                        "integrationId": 12,
                        "displayName": "Pooja Mehta",
                        "orphanType": "UNMATCHED_ACCOUNT",
                    }
                ],
            },
        },
    )

    assert narrowed.current_account is not None
    assert narrowed.current_account.label == "Pooja Mehta"
    assert narrowed.last_filters["filters"] == {"integrationId": 12}
    assert narrowed.last_filters["resultCount"] == 19
