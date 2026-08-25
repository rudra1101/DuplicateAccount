import pytest

from app.ai.agent_service import run_identity_agent

pytestmark = pytest.mark.rudrix_live


def find_tool(response, name: str):
    for tool in response.toolsUsed:
        if tool.name == name:
            return tool
    return None


def assert_no_meta_leakage(message: str):
    lowered = message.lower()
    banned = [
        "based on the provided json",
        "correct final response",
        "this response follows the rules",
        "according to the tool result",
        "the response should be",
        "according to the function response",
        "here is an answer to the original user question",
        '"name": "get_',
        '"parameters":',
    ]
    for phrase in banned:
        assert phrase not in lowered


def test_system_duplicate_count_routes_to_dashboard(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory("How many duplicate accounts do we have?"),
    )
    assert find_tool(response, "get_dashboard_summary") is not None
    assert_no_meta_leakage(response.message)
    assert response.message.strip()


def test_candidate_confidence_above_90_routes_to_confidence_breakdown(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "How many duplicate accounts have more than 90% confidence?"
        ),
    )
    tool = find_tool(response, "get_confidence_breakdown")
    assert tool is not None
    assert float(tool.arguments["minimum_confidence"]) == 90.0
    assert tool.arguments["operator"] == "gt"
    assert_no_meta_leakage(response.message)


def test_at_least_95_uses_gte(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "How many accounts have at least 95% confidence?"
        ),
    )
    tool = find_tool(response, "get_confidence_breakdown")
    assert tool is not None
    assert float(tool.arguments["minimum_confidence"]) == 95.0
    assert tool.arguments["operator"] == "gte"


def test_application_wise_confidence_routes_to_confidence_breakdown(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "Give me application-wise duplicate accounts above 90% confidence."
        ),
    )
    tool = find_tool(response, "get_confidence_breakdown")
    assert tool is not None
    assert float(tool.arguments["minimum_confidence"]) == 90.0
    assert tool.arguments["operator"] == "gt"


def test_follow_up_application_wise_keeps_previous_threshold(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "give me application wise data",
            history=[
                ("user", "accounts with more than 90% confidence"),
                (
                    "assistant",
                    "There are matching duplicate candidate accounts above 90% confidence.",
                ),
            ],
        ),
    )
    tool = find_tool(response, "get_confidence_breakdown")
    assert tool is not None
    assert float(tool.arguments["minimum_confidence"]) == 90.0
    assert tool.arguments["operator"] == "gt"


def test_group_listing_routes_to_group_search(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "Show top 10 duplicate groups above 95% confidence in SAP."
        ),
    )
    tool = find_tool(response, "search_duplicate_groups")
    assert tool is not None
    assert float(tool.arguments["minimum_confidence"]) == 95.0
    assert int(tool.arguments["limit"]) == 10


def test_scoped_duplicate_count_routes_to_duplicate_summary(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "How many duplicate accounts are in Active Directory?"
        ),
    )
    tool = find_tool(response, "get_duplicate_summary")
    assert tool is not None
    integration = str(tool.arguments.get("integration") or "").lower()
    assert "active directory" in integration or integration == "ad"


def test_policy_question_routes_to_knowledge_base(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "What is our duplicate account review policy?"
        ),
    )
    assert find_tool(response, "search_knowledge_base") is not None
    assert find_tool(response, "get_dashboard_summary") is None
    assert_no_meta_leakage(response.message)


def test_hybrid_group_policy_question_uses_live_and_knowledge_tools(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "Group 1462 looks suspicious. What does our policy say I should do?"
        ),
    )
    assert find_tool(response, "get_duplicate_group_details") is not None
    assert find_tool(response, "search_knowledge_base") is not None
    assert_no_meta_leakage(response.message)


def test_identity_vs_account_explanation_does_not_require_live_metrics(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory(
            "Explain the difference between an identity and an account in this platform."
        ),
    )
    assert find_tool(response, "get_dashboard_summary") is None
    assert find_tool(response, "get_confidence_breakdown") is None
    assert_no_meta_leakage(response.message)
    assert response.message.strip()


def test_live_answer_does_not_invent_source_section(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    response = run_identity_agent(
        db=db_session,
        request=chat_request_factory("How many duplicate accounts do we have?"),
    )
    assert response.sources == []
    assert "\nsource:" not in response.message.lower()
    assert "\nsources:" not in response.message.lower()
