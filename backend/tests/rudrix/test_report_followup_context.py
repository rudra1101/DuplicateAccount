from types import SimpleNamespace

from app.ai.fast_agent_service import (
    _apply_report_followup_context,
    _infer_followup_report_type,
    _is_referential_report_request,
)


def test_duplicate_followup_report_keeps_previous_subject_and_integration(
    chat_request_factory,
    monkeypatch,
):
    request = chat_request_factory(
        "generate a report for those accounts",
        history=[
            ("user", "how many duplicates AD have"),
            (
                "assistant",
                "The Active Directory integration has 42 duplicate accounts.",
            ),
        ],
    )

    monkeypatch.setattr(
        "app.ai.fast_agent_service._resolve_integration_id",
        lambda db, name: 7 if name == "Active Directory" else None,
    )

    call = SimpleNamespace(
        name="generate_report",
        arguments={
            "report_type": "accounts",
            "filters": {},
        },
    )

    _apply_report_followup_context(
        db=object(),
        request=request,
        tool_calls=[call],
    )

    assert call.arguments["report_type"] == "duplicate_candidates"
    assert call.arguments["filters"]["integrationId"] == 7


def test_followup_report_keeps_immediate_confidence_scope_only(
    chat_request_factory,
):
    request = chat_request_factory(
        "export those results",
        history=[
            (
                "user",
                "show duplicate accounts above 95% confidence",
            ),
            (
                "assistant",
                "There are 31 duplicate candidate accounts above 95% confidence.",
            ),
        ],
    )

    call = {
        "name": "generate_report",
        "arguments": {
            "report_type": "accounts",
            "filters": {},
        },
    }

    _apply_report_followup_context(
        db=object(),
        request=request,
        tool_calls=[call],
    )

    arguments = call["arguments"]
    assert arguments["report_type"] == "duplicate_candidates"
    assert arguments["filters"]["minimumConfidence"] == 95.0


def test_explicit_new_report_subject_is_not_overridden(
    chat_request_factory,
):
    request = chat_request_factory(
        "generate an account inventory report for those users",
        history=[
            ("user", "how many duplicates AD have"),
            (
                "assistant",
                "The Active Directory integration has 42 duplicate accounts.",
            ),
        ],
    )

    assert not _is_referential_report_request(request)


def test_duplicate_context_maps_to_duplicate_candidate_report():
    assert (
        _infer_followup_report_type(
            "The Active Directory integration has 42 duplicate accounts."
        )
        == "duplicate_candidates"
    )
