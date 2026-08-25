from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.ai import agent_service
from app.ai.config import AISettings
from app.ai.providers.base import ProviderResponse, ProviderToolCall


@dataclass
class ScriptedStep:
    text: str = ""
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None


class ScriptedProvider:
    def __init__(self, steps: list[ScriptedStep]):
        self.steps = list(steps)
        self.calls: list[dict[str, Any]] = []

    def chat(self, *, model: str, messages, tools):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "tools": tools,
            }
        )
        if not self.steps:
            raise AssertionError("Scripted provider received an unexpected extra chat call")

        step = self.steps.pop(0)
        tool_calls = []
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": step.text,
        }

        if step.tool_name is not None:
            tool_calls = [
                ProviderToolCall(
                    name=step.tool_name,
                    arguments=step.arguments or {},
                )
            ]
            assistant_message["tool_calls"] = [
                {
                    "name": step.tool_name,
                    "arguments": step.arguments or {},
                }
            ]

        return ProviderResponse(
            text=step.text,
            assistant_message=assistant_message,
            tool_calls=tool_calls,
            model=model,
        )

    def embed(self, *, model: str, inputs: list[str]):
        raise AssertionError("Embedding should not be used in response regression tests")


class FakeRegistry:
    def __init__(
        self,
        results: dict[str, Any] | None = None,
        failures: set[str] | None = None,
    ):
        self.results = results or {}
        self.failures = failures or set()
        self.executions: list[tuple[str, dict[str, Any]]] = []

    def definitions(self):
        names = set(self.results) | self.failures
        return [
            {
                "name": name,
                "description": f"Regression fake for {name}",
                "parameters": {"type": "object", "properties": {}},
            }
            for name in sorted(names)
        ]

    def execute(self, *, name: str, db, arguments: dict[str, Any]):
        self.executions.append((name, dict(arguments)))
        if name in self.failures:
            raise RuntimeError(f"{name} unavailable")
        return self.results[name]


def install_runtime(monkeypatch, *, provider: ScriptedProvider, registry: FakeRegistry):
    settings = AISettings(
        provider="test",
        ollama_base_url="http://unused",
        fast_model="rudrix-fast-test",
        reasoning_model="rudrix-reasoning-test",
        embedding_model="unused",
        max_tool_iterations=6,
        default_timezone="Asia/Kolkata",
    )

    monkeypatch.setattr(agent_service, "get_ai_settings", lambda: settings)
    monkeypatch.setattr(
        agent_service.AIProviderFactory,
        "create",
        lambda _settings: provider,
    )
    monkeypatch.setattr(agent_service, "create_ai_tool_registry", lambda: registry)


def assert_clean_user_answer(message: str):
    lowered = message.lower()
    banned = [
        "based on the provided json",
        "according to the tool result",
        "according to the function response",
        "correct final response",
        "this response follows the rules",
        '"name": "get_',
        '"parameters":',
        "tool call",
        "raw json",
    ]
    for phrase in banned:
        assert phrase not in lowered


def test_system_duplicate_count_returns_duplicate_accounts_not_accounts_scanned(
    monkeypatch,
    chat_request_factory,
):
    provider = ScriptedProvider(
        [
            ScriptedStep(tool_name="get_dashboard_summary", arguments={}),
            ScriptedStep(text="There are 847 duplicate accounts across all current integrations."),
        ]
    )
    registry = FakeRegistry(
        results={
            "get_dashboard_summary": {
                "summary": {
                    "duplicateAccounts": 847,
                    "accountsScanned": 52000,
                }
            }
        }
    )
    install_runtime(monkeypatch, provider=provider, registry=registry)

    response = agent_service.run_identity_agent(
        db=object(),
        request=chat_request_factory("How many duplicate accounts do we have?"),
    )

    assert response.message == "There are 847 duplicate accounts across all current integrations."
    assert "847" in response.message
    assert "52000" not in response.message
    assert response.toolsUsed[0].name == "get_dashboard_summary"
    assert response.sources == []
    assert_clean_user_answer(response.message)


def test_confidence_response_uses_authoritative_matching_account_total(
    monkeypatch,
    chat_request_factory,
):
    provider = ScriptedProvider(
        [
            ScriptedStep(
                tool_name="get_confidence_breakdown",
                arguments={
                    "minimum_confidence": "90",
                    "operator": "gt",
                    "integration": None,
                },
            ),
            ScriptedStep(text="There are 126 duplicate candidate accounts above 90% confidence."),
        ]
    )
    registry = FakeRegistry(
        results={
            "get_confidence_breakdown": {
                "totalMatchingAccounts": 126,
                "applications": [
                    {"application": "AD", "matchingAccounts": 90},
                    {"application": "SAP", "matchingAccounts": 36},
                ],
            }
        }
    )
    install_runtime(monkeypatch, provider=provider, registry=registry)

    response = agent_service.run_identity_agent(
        db=object(),
        request=chat_request_factory(
            "How many duplicate accounts have more than 90% confidence?"
        ),
    )

    tool = response.toolsUsed[0]
    assert tool.name == "get_confidence_breakdown"
    assert tool.arguments["minimum_confidence"] == 90.0
    assert tool.arguments["operator"] == "gt"
    assert response.message == "There are 126 duplicate candidate accounts above 90% confidence."
    assert_clean_user_answer(response.message)


def test_application_wise_response_keeps_compact_table_contract(
    monkeypatch,
    chat_request_factory,
):
    expected = (
        "| Application | Matching accounts |\n"
        "|---|---:|\n"
        "| Active Directory | 90 |\n"
        "| SAP | 36 |\n"
        "\n**Total: 126 duplicate candidate accounts above 90% confidence.**"
    )
    provider = ScriptedProvider(
        [
            ScriptedStep(
                tool_name="get_confidence_breakdown",
                arguments={"minimum_confidence": 90, "operator": "gt"},
            ),
            ScriptedStep(text=expected),
        ]
    )
    registry = FakeRegistry(
        results={
            "get_confidence_breakdown": {
                "totalMatchingAccounts": 126,
                "applications": [
                    {"application": "Active Directory", "matchingAccounts": 90},
                    {"application": "SAP", "matchingAccounts": 36},
                ],
            }
        }
    )
    install_runtime(monkeypatch, provider=provider, registry=registry)

    response = agent_service.run_identity_agent(
        db=object(),
        request=chat_request_factory(
            "Give me application-wise duplicate accounts above 90% confidence."
        ),
    )

    assert response.message == expected
    assert "Active Directory" in response.message
    assert "SAP" in response.message
    assert "126" in response.message
    assert_clean_user_answer(response.message)


def test_knowledge_response_returns_structured_sources_without_raw_metadata(
    monkeypatch,
    chat_request_factory,
):
    provider = ScriptedProvider(
        [
            ScriptedStep(
                tool_name="search_knowledge_base",
                arguments={
                    "query": "duplicate account review policy",
                    "limit": 5,
                    "minimum_similarity": 0.5,
                    "document_id": None,
                },
            ),
            ScriptedStep(
                text=(
                    "Reviewers must validate the identity evidence and document the "
                    "decision before remediation."
                )
            ),
        ]
    )
    registry = FakeRegistry(
        results={
            "search_knowledge_base": {
                "answerContext": "Reviewers must validate evidence and document decisions.",
                "sources": [
                    {
                        "documentId": 7,
                        "documentName": "duplicate_review_policy.pdf",
                        "pageNumber": 4,
                    }
                ],
            }
        }
    )
    install_runtime(monkeypatch, provider=provider, registry=registry)

    response = agent_service.run_identity_agent(
        db=object(),
        request=chat_request_factory("What is our duplicate account review policy?"),
    )

    assert len(response.sources) == 1
    assert response.sources[0].documentId == 7
    assert response.sources[0].documentName == "duplicate_review_policy.pdf"
    assert response.sources[0].pageNumber == 4
    assert "documentId" not in response.message
    assert "similarity" not in response.message.lower()
    assert "Source:" not in response.message
    assert_clean_user_answer(response.message)


def test_hybrid_response_keeps_live_facts_and_policy_guidance_separate(
    monkeypatch,
    chat_request_factory,
):
    expected = (
        "## Current System Data\n"
        "Group 1462 contains 2 candidate accounts with a highest confidence of 97%.\n\n"
        "## Policy Guidance\n"
        "Validate the matching identity evidence and record the reviewer decision before remediation."
    )
    provider = ScriptedProvider(
        [
            ScriptedStep(
                tool_name="get_duplicate_group_details",
                arguments={"group_id": 1462},
            ),
            ScriptedStep(
                tool_name="search_knowledge_base",
                arguments={"query": "duplicate account review policy", "limit": 5},
            ),
            ScriptedStep(text=expected),
        ]
    )
    registry = FakeRegistry(
        results={
            "get_duplicate_group_details": {
                "groupId": 1462,
                "duplicateCount": 2,
                "highestConfidence": 97,
            },
            "search_knowledge_base": {
                "sources": [
                    {
                        "documentId": 7,
                        "documentName": "duplicate_review_policy.pdf",
                        "pageNumber": 4,
                    }
                ],
            },
        }
    )
    install_runtime(monkeypatch, provider=provider, registry=registry)

    response = agent_service.run_identity_agent(
        db=object(),
        request=chat_request_factory(
            "Group 1462 looks suspicious. What does our policy say I should do?"
        ),
    )

    assert response.message == expected
    assert "## Current System Data" in response.message
    assert "## Policy Guidance" in response.message
    assert [tool.name for tool in response.toolsUsed] == [
        "get_duplicate_group_details",
        "search_knowledge_base",
    ]
    assert len(response.sources) == 1
    assert_clean_user_answer(response.message)


def test_tool_failure_is_not_reported_as_zero_results(
    monkeypatch,
    chat_request_factory,
):
    provider = ScriptedProvider(
        [
            ScriptedStep(tool_name="get_dashboard_summary", arguments={}),
            ScriptedStep(text="The requested current data could not be retrieved."),
        ]
    )
    registry = FakeRegistry(failures={"get_dashboard_summary"})
    install_runtime(monkeypatch, provider=provider, registry=registry)

    response = agent_service.run_identity_agent(
        db=object(),
        request=chat_request_factory("How many duplicate accounts do we have?"),
    )

    assert response.toolsUsed[0].result["success"] is False
    assert response.message == "The requested current data could not be retrieved."
    assert "0 duplicate" not in response.message.lower()
    assert "no duplicate" not in response.message.lower()
    assert_clean_user_answer(response.message)


def test_reasoning_model_selection_does_not_change_response_contract(
    monkeypatch,
    chat_request_factory,
):
    provider = ScriptedProvider(
        [
            ScriptedStep(tool_name="get_dashboard_summary", arguments={}),
            ScriptedStep(text="There are 847 duplicate accounts across all current integrations."),
        ]
    )
    registry = FakeRegistry(
        results={"get_dashboard_summary": {"summary": {"duplicateAccounts": 847}}}
    )
    install_runtime(monkeypatch, provider=provider, registry=registry)

    response = agent_service.run_identity_agent(
        db=object(),
        request=chat_request_factory(
            "How many duplicate accounts do we have?",
            reasoning=True,
        ),
    )

    assert response.model == "rudrix-reasoning-test"
    assert provider.calls[0]["model"] == "rudrix-reasoning-test"
    assert response.message == "There are 847 duplicate accounts across all current integrations."
    assert_clean_user_answer(response.message)
