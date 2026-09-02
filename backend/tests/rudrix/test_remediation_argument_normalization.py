from __future__ import annotations

from app.ai.tools.remediation_action_tools import (
    RudrixRemediationOperationsTool,
    normalize_remediation_arguments,
)


def test_null_like_remediation_arguments_are_normalized():
    normalized = normalize_remediation_arguments(
        {
            "operation": "null",
            "search": "None",
            "application": "null",
            "status": "null",
            "minimum_confidence": "null",
            "limit": "undefined",
            "item_id": "",
            "comment": "n/a",
        }
    )

    assert normalized == {
        "operation": "SEARCH",
        "search": None,
        "application": None,
        "status": None,
        "minimum_confidence": None,
        "limit": 10,
        "item_id": None,
        "comment": None,
    }


def test_invalid_optional_search_values_do_not_break_list_request(monkeypatch):
    captured = {}

    def fake_execute(self, *, db, arguments):
        captured.update(arguments)
        return {"count": 2, "items": [{"id": 1}, {"id": 2}]}

    from app.ai.tools import workflow_action_tools

    monkeypatch.setattr(
        workflow_action_tools.RudrixRemediationOperationsTool,
        "execute",
        fake_execute,
    )

    tool = RudrixRemediationOperationsTool()
    result = tool.execute(
        db=object(),
        arguments={
            "search": "null",
            "application": "None",
            "status": "undefined",
            "minimum_confidence": "null",
            "limit": None,
        },
    )

    assert result["count"] == 2
    assert captured["operation"] == "SEARCH"
    assert captured["search"] is None
    assert captured["application"] is None
    assert captured["status"] is None
    assert captured["minimum_confidence"] is None
    assert captured["limit"] == 10


def test_numeric_remediation_filters_are_safely_coerced():
    normalized = normalize_remediation_arguments(
        {
            "operation": "search",
            "minimum_confidence": "95",
            "limit": "500",
            "item_id": "12",
        }
    )

    assert normalized["operation"] == "SEARCH"
    assert normalized["minimum_confidence"] == 95.0
    assert normalized["limit"] == 50
    assert normalized["item_id"] == 12
