from __future__ import annotations

from app.ai.agent_core.models import AgentState
from app.ai.fast_agent_service import _state_instruction
from app.ai.agent_core.state import reduce_tool_result


def test_report_filters_are_persisted_as_grounded_state():
    state = AgentState(
        last_filters={
            "context": "orphan_accounts",
            "reportType": "orphan_accounts",
            "filters": {
                "integrationId": 7,
                "dateFrom": "2026-09-09",
            },
        }
    )

    rendered = _state_instruction(state)

    assert "orphan_accounts" in rendered
    assert "integrationId" in rendered
    assert "2026-09-09" in rendered


def test_successful_report_result_updates_grounded_filter_state():
    state = AgentState()
    updated = reduce_tool_result(
        state,
        tool_name="generate_report",
        tool_result={
            "success": True,
            "data": {
                "reportType": "duplicate_candidates",
                "downloadUrl": "/reports/rudrix-download?reportType=duplicate_candidates",
                "clientAction": {
                    "filters": {
                        "integrationId": 12,
                        "minimumConfidence": 95,
                    }
                },
            },
        },
    )

    assert updated.last_filters["reportType"] == "duplicate_candidates"
    assert updated.last_filters["filters"]["integrationId"] == 12
    assert updated.last_filters["filters"]["minimumConfidence"] == 95
