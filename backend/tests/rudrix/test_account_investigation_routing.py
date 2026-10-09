from app.ai.fast_agent_service import _select_definitions
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.account_investigation_tools import (
    InvestigateAccountsTool,
    _normalize_account_query,
    _optional_filter,
)
from app.schemas.chat import ChatHistoryMessage, ChatRequest


def _selected_names(message: str, history=None) -> set[str]:
    request = ChatRequest(
        message=message,
        conversationId=None,
        history=history or [],
        useReasoningModel=False,
    )
    definitions = create_ai_tool_registry().definitions()
    selected = _select_definitions(definitions, request)
    return {str(item.get("name") or "") for item in selected}


def test_account_capability_is_available_for_non_trivial_agent_turns():
    assert "investigate_accounts" in _selected_names("Find account jsmith")
    assert "investigate_accounts" in _selected_names("Explain the principle of least privilege")


def test_followup_keeps_full_authorized_capability_surface_available():
    history = [
        ChatHistoryMessage(
            role="assistant",
            content="I found jsmith in Active Directory and ServiceNow.",
        )
    ]
    names = _selected_names("Why is that one orphaned?", history=history)
    assert "investigate_accounts" in names
    assert "search_orphan_accounts" in names
    assert "search_knowledge_base" in names


def test_only_query_is_required_for_account_investigation():
    tool = InvestigateAccountsTool()
    assert tool.parameters["required"] == ["query"]


def test_account_investigation_does_not_expose_orphan_only_filter():
    tool = InvestigateAccountsTool()
    assert "orphan_only" not in tool.parameters["properties"]


def test_optional_filter_treats_model_null_strings_as_omitted():
    for value in (
        None,
        "",
        "null",
        "NULL",
        "none",
        "undefined",
        "N/A",
        "any",
        "null application",
        "null integration",
        "the null application",
        "the null integration",
        "application is null",
        "integration is undefined",
    ):
        assert _optional_filter(value) == ""


def test_optional_filter_preserves_real_filter_values():
    assert _optional_filter("Active Directory") == "Active Directory"
    assert _optional_filter("Workday") == "Workday"


def test_account_query_normalizes_full_find_sentence():
    assert _normalize_account_query("find account for Aditya Sinha") == "Aditya Sinha"


def test_account_query_handles_common_typo_and_search_phrases():
    assert _normalize_account_query("find accout for Aditya Sinha") == "Aditya Sinha"
    assert _normalize_account_query("search for account W00003") == "W00003"


def test_account_query_preserves_actual_account_values():
    assert _normalize_account_query("W00003") == "W00003"
    assert _normalize_account_query("asinha@examplecorp.com") == "asinha@examplecorp.com"
