from __future__ import annotations

from app.ai.authorization import reset_rudrix_permissions, set_rudrix_permissions
from app.ai.fast_agent_service import _select_definitions, _trim_messages
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.action_tools import NavigateAppTool
from app.schemas.chat import ChatRequest


def _selected_names(message: str) -> set[str]:
    request = ChatRequest(message=message, history=[])
    definitions = create_ai_tool_registry().definitions()
    return {
        item["name"]
        for item in _select_definitions(definitions, request)
    }


def test_orphan_request_retrieves_orphan_capability_and_grounding_fallbacks():
    names = _selected_names("Show orphan accounts from Active Directory")

    assert "search_orphan_accounts" in names
    assert "search_identityai_product_knowledge" in names
    assert "search_knowledge_base" in names
    assert len(names) < len(create_ai_tool_registry().definitions())


def test_report_request_retrieves_report_capability():
    names = _selected_names("Generate a duplicate report above 95%")

    assert "generate_report" in names
    assert "search_duplicate_groups" in names or "get_duplicate_summary" in names


def test_remediation_request_retrieves_remediation_capabilities():
    names = _selected_names("Create a remediation ticket for this account")

    assert "create_remediation_ticket" in names
    assert "search_remediation_items" in names


def test_product_question_always_has_builtin_product_knowledge():
    names = _selected_names("How does IdentityAI work?")

    assert "search_identityai_product_knowledge" in names


def test_trivial_conversation_does_not_send_tool_schema_overhead():
    assert _selected_names("hello") == set()


def test_message_trimming_keeps_system_and_recent_context():
    messages = [{"role": "system", "content": "system"}]
    messages.extend(
        {"role": "user", "content": f"message-{index}"}
        for index in range(20)
    )

    trimmed = _trim_messages(messages)

    assert trimmed[0]["role"] == "system"
    assert trimmed[-1]["content"] == "message-19"
    assert len(trimmed) == 13


def test_navigation_tool_enforces_destination_permission():
    tool = NavigateAppTool()
    token = set_rudrix_permissions({"report.view"})
    try:
        result = tool.execute(
            db=object(),
            arguments={
                "destination": "reports",
                "application": None,
                "integration_id": None,
            },
        )
        assert result["route"] == "/account-intelligence/reports"

        try:
            tool.execute(
                db=object(),
                arguments={
                    "destination": "settings",
                    "application": None,
                    "integration_id": None,
                },
            )
        except PermissionError:
            pass
        else:
            raise AssertionError("Settings navigation should require settings.manage")
    finally:
        reset_rudrix_permissions(token)


def test_action_tools_are_hidden_by_rbac():
    token = set_rudrix_permissions({"report.view"})
    try:
        names = {
            definition["name"]
            for definition in create_ai_tool_registry().definitions()
        }
    finally:
        reset_rudrix_permissions(token)

    assert "generate_report" in names
    assert "create_remediation_ticket" not in names
    assert "search_remediation_items" not in names
    assert "navigate_app" in names
    assert "search_identityai_product_knowledge" in names
