from __future__ import annotations

from app.ai.authorization import reset_rudrix_permissions, set_rudrix_permissions
from app.ai.fast_agent_service import _select_definitions, _trim_messages
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.action_tools import NavigateAppTool
from app.schemas.chat import ChatHistoryMessage, ChatRequest


def _selected_names(message: str, history: list[ChatHistoryMessage] | None = None) -> set[str]:
    request = ChatRequest(
        message=message,
        history=history or [],
    )
    definitions = create_ai_tool_registry().definitions()
    return {
        item["name"]
        for item in _select_definitions(definitions, request)
    }


def test_report_request_routes_to_report_tool():
    names = _selected_names("Generate a duplicate candidates report above 95% confidence")
    assert "generate_report" in names
    assert "get_confidence_breakdown" in names


def test_ticket_request_routes_to_search_and_create_tools():
    names = _selected_names("Create a disable ticket for this remediation item")
    assert "search_remediation_items" in names
    assert "create_remediation_ticket" in names


def test_navigation_request_routes_to_navigation_tool():
    names = _selected_names("Take me to the remediation page")
    assert "navigate_app" in names


def test_plain_explanation_avoids_tool_schema_overhead():
    names = _selected_names("Explain the difference between deterministic and probabilistic matching")
    assert names == set()


def test_follow_up_context_preserves_domain_tool_routing():
    history = [
        ChatHistoryMessage(role="user", content="Show duplicate accounts above 90% confidence"),
        ChatHistoryMessage(role="assistant", content="There are matching accounts."),
    ]
    names = _selected_names("Give me the application-wise breakdown", history)
    assert "get_confidence_breakdown" in names


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
        assert result["route"] == "/reports"

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
