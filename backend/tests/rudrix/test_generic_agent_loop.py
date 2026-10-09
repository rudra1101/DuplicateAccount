from __future__ import annotations

from types import SimpleNamespace

from app.ai.fast_agent_service import run_identity_agent_stream_fast
from app.ai.providers.base import ProviderResponse, ProviderToolCall
from app.schemas.chat import ChatRequest


def test_generic_agent_can_chain_capabilities_in_one_user_turn(monkeypatch):
    class FakeProvider:
        def __init__(self):
            self.calls = 0

        def stream_chat(self, *, model, messages, tools):
            self.calls += 1
            tool_names = {item["name"] for item in tools}
            assert tool_names == {"search_orphan_accounts", "generate_report"}

            if self.calls == 1:
                response = ProviderResponse(
                    text="",
                    assistant_message={"role": "assistant", "content": ""},
                    tool_calls=[
                        ProviderToolCall(
                            name="search_orphan_accounts",
                            arguments={"integration": "Active Directory", "limit": 20},
                        )
                    ],
                    model=model,
                )
            elif self.calls == 2:
                # The first grounded tool result must already be available when the
                # model chooses the second capability.
                assert "orphan_accounts" in str(messages)
                assert "integrationId" in str(messages)
                response = ProviderResponse(
                    text="",
                    assistant_message={"role": "assistant", "content": ""},
                    tool_calls=[
                        ProviderToolCall(
                            name="generate_report",
                            arguments={
                                "report_type": "orphan_accounts",
                                "filters": {"integrationId": 12},
                            },
                        )
                    ],
                    model=model,
                )
            else:
                response = ProviderResponse(
                    text="Generated the Active Directory orphan account report.",
                    assistant_message={
                        "role": "assistant",
                        "content": "Generated the Active Directory orphan account report.",
                    },
                    tool_calls=[],
                    model=model,
                )

            yield {"type": "result", "response": response}

    class FakeRegistry:
        def definitions(self):
            return [
                {
                    "name": "search_orphan_accounts",
                    "description": "Search current orphan accounts.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
                {
                    "name": "generate_report",
                    "description": "Generate a report from IdentityAI data and filters.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            ]

        def execute(self, *, name, db, arguments):
            if name == "search_orphan_accounts":
                return {
                    "count": 2,
                    "items": [
                        {
                            "sourceAccountId": 201,
                            "integrationId": 12,
                            "integrationName": "Active Directory",
                            "application": "Active Directory",
                            "username": "one",
                            "orphaned": True,
                            "orphanType": "UNMATCHED_ACCOUNT",
                        },
                        {
                            "sourceAccountId": 202,
                            "integrationId": 12,
                            "integrationName": "Active Directory",
                            "application": "Active Directory",
                            "username": "two",
                            "orphaned": True,
                            "orphanType": "AMBIGUOUS_CORRELATION",
                        },
                    ],
                    "reportType": "orphan_accounts",
                    "reportFilters": {"integrationId": 12},
                }
            if name == "generate_report":
                assert arguments["filters"]["integrationId"] == 12
                return {
                    "reportType": "orphan_accounts",
                    "total": 2,
                    "downloadUrl": "/reports/rudrix-download?reportType=orphan_accounts&integrationId=12",
                    "clientAction": {"filters": {"integrationId": 12}},
                }
            raise AssertionError(name)

    provider = FakeProvider()
    monkeypatch.setattr(
        "app.ai.fast_agent_service.get_ai_settings",
        lambda: SimpleNamespace(
            fast_model="fast-model",
            reasoning_model="reasoning-model",
            max_tool_iterations=6,
        ),
    )
    monkeypatch.setattr(
        "app.ai.fast_agent_service.AIProviderFactory.create",
        lambda settings: provider,
    )
    monkeypatch.setattr(
        "app.ai.fast_agent_service.create_ai_tool_registry",
        lambda: FakeRegistry(),
    )

    events = list(
        run_identity_agent_stream_fast(
            db=object(),
            request=ChatRequest(
                message="Show Active Directory orphan accounts and generate a report for them."
            ),
        )
    )

    done = next(event for event in events if event["type"] == "done")
    response = done["response"]

    assert provider.calls == 3
    assert [tool.name for tool in response.toolsUsed] == [
        "search_orphan_accounts",
        "generate_report",
    ]
    assert response.message == "Generated the Active Directory orphan account report."
