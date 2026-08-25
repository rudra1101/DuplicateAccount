from app.ai.agent_service import (
    build_messages,
    extract_chat_sources,
    extract_text_tool_calls,
    normalize_tool_arguments,
)


def test_build_messages_preserves_history_and_current_user_message(chat_request_factory):
    request = chat_request_factory(
        "give me application wise data",
        history=[
            ("user", "accounts with more than 90% confidence"),
            ("assistant", "There are matching accounts."),
        ],
    )
    messages = build_messages(request)
    assert messages[0]["role"] == "system"
    assert messages[-1] == {
        "role": "user",
        "content": "give me application wise data",
    }
    assert messages[-3]["content"] == "accounts with more than 90% confidence"
    assert messages[-2]["role"] == "assistant"


def test_extract_text_tool_calls_accepts_arguments():
    content = (
        'I should use this: '
        '{"name":"get_confidence_breakdown",'
        '"arguments":{"minimum_confidence":90,"operator":"gt"}}'
    )
    result = extract_text_tool_calls(content, {"get_confidence_breakdown"})
    assert result == [
        {
            "name": "get_confidence_breakdown",
            "arguments": {
                "minimum_confidence": 90,
                "operator": "gt",
            },
        }
    ]


def test_extract_text_tool_calls_rejects_unknown_tool():
    content = '{"name":"drop_database","arguments":{}}'
    assert extract_text_tool_calls(content, {"get_dashboard_summary"}) == []


def test_confidence_argument_is_normalized_to_number():
    result = normalize_tool_arguments(
        "get_confidence_breakdown",
        {
            "minimum_confidence": "90",
            "operator": "gt",
        },
    )
    assert result["minimum_confidence"] == 90.0


def test_knowledge_search_arguments_are_bounded_and_null_normalized():
    result = normalize_tool_arguments(
        "search_knowledge_base",
        {
            "limit": 999,
            "minimum_similarity": -5,
            "document_id": "null",
        },
    )
    assert result["limit"] == 8
    assert result["minimum_similarity"] == 0.0
    assert result["document_id"] is None


def test_extract_chat_sources_only_returns_successful_knowledge_sources():
    result = extract_chat_sources(
        tool_name="search_knowledge_base",
        tool_result={
            "success": True,
            "data": {
                "sources": [
                    {
                        "documentId": 7,
                        "documentName": "duplicate_review_policy.pdf",
                        "pageNumber": 4,
                    },
                    {
                        "documentId": 7,
                        "documentName": "duplicate_review_policy.pdf",
                        "pageNumber": 4,
                    },
                ]
            },
        },
    )
    assert len(result) == 1
    assert result[0].documentId == 7
    assert result[0].documentName == "duplicate_review_policy.pdf"
    assert result[0].pageNumber == 4


def test_live_tool_never_creates_document_sources():
    result = extract_chat_sources(
        tool_name="get_dashboard_summary",
        tool_result={
            "success": True,
            "data": {"duplicateAccounts": 100},
        },
    )
    assert result == []
