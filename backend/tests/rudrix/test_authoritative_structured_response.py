from app.schemas.chat import ChatResponse, ToolInvocationResponse


def _tool(name: str, data: dict):
    return ToolInvocationResponse(
        name=name,
        arguments={},
        result={"success": True, "data": data},
    )


def test_live_record_items_override_generic_model_greeting():
    response = ChatResponse(
        conversationId="conversation-1",
        message=(
            "I'm Rudrix, the AI copilot for IdentityAI. I'm here to assist you "
            "with your identity and IAM work. What's your goal?"
        ),
        model="llama3.1:8b",
        toolsUsed=[
            _tool(
                "search_orphan_accounts",
                {
                    "count": 2,
                    "message": "Found 2 current orphan account(s).",
                    "items": [
                        {
                            "sourceAccountId": 101,
                            "displayName": "Pooja Mehta",
                            "application": "Active Directory",
                            "orphanType": "UNMATCHED_ACCOUNT",
                            "reason": "NO_MATCH",
                        },
                        {
                            "sourceAccountId": 102,
                            "displayName": "Rudra Reddy",
                            "application": "Active Directory",
                            "orphanType": "UNMATCHED_ACCOUNT",
                            "reason": "NO_MATCH",
                        },
                    ],
                },
            )
        ],
        sources=[],
    )

    assert response.message.startswith("Found 2 current orphan account(s).")
    assert "Pooja Mehta" in response.message
    assert "Rudra Reddy" in response.message
    assert "UNMATCHED_ACCOUNT" in response.message
    assert "What's your goal" not in response.message


def test_empty_live_record_items_use_authoritative_empty_message():
    response = ChatResponse(
        conversationId="conversation-2",
        message="What would you like to accomplish?",
        model="llama3.1:8b",
        toolsUsed=[
            _tool(
                "search_orphan_accounts",
                {
                    "count": 0,
                    "message": "No current orphan accounts matched those filters.",
                    "items": [],
                },
            )
        ],
        sources=[],
    )

    assert response.message == "No current orphan accounts matched those filters."


def test_non_record_tool_keeps_model_synthesis():
    response = ChatResponse(
        conversationId="conversation-3",
        message="Orphan accounts are accounts that are not correlated to an identity.",
        model="llama3.1:8b",
        toolsUsed=[
            _tool(
                "search_identityai_product_knowledge",
                {
                    "message": "Product documentation found.",
                    "sources": [{"title": "Orphan accounts"}],
                },
            )
        ],
        sources=[],
    )

    assert response.message == (
        "Orphan accounts are accounts that are not correlated to an identity."
    )


def test_later_successful_action_supersedes_earlier_record_read():
    response = ChatResponse(
        conversationId="conversation-4",
        message="Generated the Active Directory orphan account report.",
        model="llama3.1:8b",
        toolsUsed=[
            _tool(
                "search_orphan_accounts",
                {
                    "count": 2,
                    "items": [
                        {
                            "sourceAccountId": 101,
                            "displayName": "Pooja Mehta",
                            "application": "Active Directory",
                            "orphanType": "UNMATCHED_ACCOUNT",
                        },
                        {
                            "sourceAccountId": 102,
                            "displayName": "Rudra Reddy",
                            "application": "Active Directory",
                            "orphanType": "AMBIGUOUS_CORRELATION",
                        },
                    ],
                },
            ),
            _tool(
                "generate_report",
                {
                    "message": "Generated the Active Directory orphan account report.",
                    "reportId": 44,
                },
            ),
        ],
        sources=[],
    )

    assert response.message == "Generated the Active Directory orphan account report."
