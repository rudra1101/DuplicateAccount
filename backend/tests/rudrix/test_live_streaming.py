import pytest

from app.ai.agent_service import run_identity_agent_stream

pytestmark = [pytest.mark.rudrix_live, pytest.mark.rudrix_stream]


def test_stream_emits_status_delta_and_done(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    events = list(
        run_identity_agent_stream(
            db=db_session,
            request=chat_request_factory(
                "How many duplicate accounts do we have?"
            ),
        )
    )
    event_types = [event["type"] for event in events]
    assert "status" in event_types
    assert "delta" in event_types
    assert event_types[-1] == "done"

    deltas = "".join(
        event["text"]
        for event in events
        if event["type"] == "delta"
    ).strip()
    assert deltas

    done_response = events[-1]["response"]
    assert done_response.message.strip()
    assert done_response.message.strip() == deltas


def test_stream_uses_dashboard_tool_for_system_duplicate_count(
    require_live_rudrix,
    chat_request_factory,
    db_session,
):
    events = list(
        run_identity_agent_stream(
            db=db_session,
            request=chat_request_factory(
                "How many duplicate accounts do we have?"
            ),
        )
    )
    done_response = events[-1]["response"]
    assert any(
        tool.name == "get_dashboard_summary"
        for tool in done_response.toolsUsed
    )
