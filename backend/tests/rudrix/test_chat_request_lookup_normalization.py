from app.ai.fast_agent_service import _select_definitions
from app.ai.tools import create_ai_tool_registry
from app.schemas.chat import ChatHistoryMessage, ChatRequest


def _selected_names(request: ChatRequest) -> set[str]:
    definitions = create_ai_tool_registry().definitions()
    selected = _select_definitions(definitions, request)
    return {str(item.get("name") or "") for item in selected}


def test_missing_f_in_find_account_is_normalized():
    request = ChatRequest(message="ind account for Aditya Sinha")

    assert request.message == "find account for Aditya Sinha"
    assert "investigate_accounts" in _selected_names(request)


def test_find_accout_typo_is_normalized():
    request = ChatRequest(message="find accout for Aditya Sinha")

    assert request.message == "find account for Aditya Sinha"
    assert "investigate_accounts" in _selected_names(request)


def test_explicit_named_lookup_drops_stale_remediation_history():
    request = ChatRequest(
        message="ind account for Aditya Sinha",
        history=[
            ChatHistoryMessage(
                role="assistant",
                content="Remediation item 203 is pending and has no ticket.",
            )
        ],
    )

    assert request.message == "find account for Aditya Sinha"
    assert request.history == []
    assert _selected_names(request) == {"investigate_accounts"}


def test_referential_lookup_keeps_history():
    history = [
        ChatHistoryMessage(
            role="assistant",
            content="Aditya Sinha was found in Active Directory.",
        )
    ]
    request = ChatRequest(
        message="find that account",
        history=history,
    )

    assert len(request.history) == 1
    assert "investigate_accounts" in _selected_names(request)


def test_non_lookup_message_is_unchanged():
    request = ChatRequest(message="Explain duplicate confidence")

    assert request.message == "Explain duplicate confidence"
