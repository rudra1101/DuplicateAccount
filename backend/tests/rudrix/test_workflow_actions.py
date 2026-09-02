from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai.authorization import (
    reset_rudrix_actor,
    reset_rudrix_permissions,
    set_rudrix_actor,
    set_rudrix_permissions,
)
from app.ai.tools.workflow_action_tools import (
    RudrixRemediationOperationsTool,
    RudrixReviewOperationsTool,
)
import app.ai.tools.workflow_action_tools as workflow_tools


def _review_args(**overrides):
    values = {
        "operation": "DECIDE",
        "integration": "Active Directory",
        "application": "Active Directory",
        "candidate_id": 42,
        "decision": "DUPLICATE",
        "comment": None,
    }
    values.update(overrides)
    return values


def _remediation_args(**overrides):
    values = {
        "operation": "SEARCH",
        "search": None,
        "application": None,
        "status": None,
        "minimum_confidence": None,
        "limit": 10,
        "item_id": None,
        "comment": None,
    }
    values.update(overrides)
    return values


def test_review_decision_requires_duplicate_review_permission(monkeypatch):
    called = False

    def fake_save(**kwargs):
        nonlocal called
        called = True
        return kwargs

    monkeypatch.setattr(workflow_tools, "save_duplicate_group_candidate_decision", fake_save)
    token = set_rudrix_permissions({"duplicate.view"})
    try:
        with pytest.raises(PermissionError, match="duplicate.review"):
            RudrixReviewOperationsTool().execute(
                db=object(),
                arguments=_review_args(),
            )
    finally:
        reset_rudrix_permissions(token)

    assert called is False


def test_review_decision_records_authenticated_actor(monkeypatch):
    captured = {}

    def fake_save(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(workflow_tools, "save_duplicate_group_candidate_decision", fake_save)
    permission_token = set_rudrix_permissions({"duplicate.view", "duplicate.review"})
    actor_token = set_rudrix_actor("Aisha Reviewer")
    try:
        result = RudrixReviewOperationsTool().execute(
            db=object(),
            arguments=_review_args(comment="Confirmed after comparison."),
        )
    finally:
        reset_rudrix_actor(actor_token)
        reset_rudrix_permissions(permission_token)

    assert captured["candidate_id"] == 42
    assert captured["decision"] == "DUPLICATE"
    assert captured["reviewer_name"] == "Aisha Reviewer"
    assert "Submitted via Rudrix" in captured["comment"]
    assert result["decision"] == "DUPLICATE"
    assert result["reviewer"] == "Aisha Reviewer"


def test_ignore_remediation_requires_manage_permission(monkeypatch):
    called = False

    def fake_update(*args, **kwargs):
        nonlocal called
        called = True
        return {"id": 9}

    monkeypatch.setattr(workflow_tools, "update_remediation_status", fake_update)
    token = set_rudrix_permissions({"remediation.view"})
    try:
        with pytest.raises(PermissionError, match="remediation.manage"):
            RudrixRemediationOperationsTool().execute(
                db=object(),
                arguments=_remediation_args(operation="IGNORE", item_id=9),
            )
    finally:
        reset_rudrix_permissions(token)

    assert called is False


def test_ignore_remediation_returns_pair_to_review_and_records_actor(monkeypatch):
    captured = {}

    def fake_update(db, **kwargs):
        captured.update(kwargs)
        return {"id": kwargs["item_id"], "status": kwargs["status"]}

    monkeypatch.setattr(workflow_tools, "update_remediation_status", fake_update)
    permission_token = set_rudrix_permissions({"remediation.view", "remediation.manage"})
    actor_token = set_rudrix_actor("IAM Operator")
    try:
        result = RudrixRemediationOperationsTool().execute(
            db=object(),
            arguments=_remediation_args(
                operation="IGNORE",
                item_id=9,
                comment="Needs another review.",
            ),
        )
    finally:
        reset_rudrix_actor(actor_token)
        reset_rudrix_permissions(permission_token)

    assert captured["status"] == "IGNORED"
    assert captured["actioned_by"] == "IAM Operator"
    assert "via Rudrix" in captured["action_comment"]
    assert result["status"] == "IGNORED"
    assert result["clientAction"]["route"] == "/review"


def test_sync_ticket_uses_existing_service_desk_flow(monkeypatch):
    monkeypatch.setattr(
        workflow_tools,
        "sync_ticket_by_id",
        lambda db, item_id: {
            "id": item_id,
            "ticketId": "INC001",
            "ticketStatus": "Resolved",
        },
    )
    token = set_rudrix_permissions({"remediation.view", "remediation.manage"})
    try:
        result = RudrixRemediationOperationsTool().execute(
            db=object(),
            arguments=_remediation_args(operation="SYNC_TICKET", item_id=15),
        )
    finally:
        reset_rudrix_permissions(token)

    assert result["ticketId"] == "INC001"
    assert result["ticketStatus"] == "Resolved"
    assert result["clientAction"]["route"] == "/remediation"


def test_history_requires_history_permission(monkeypatch):
    monkeypatch.setattr(workflow_tools, "list_decision_history", lambda db, limit: [])
    token = set_rudrix_permissions({"remediation.view"})
    try:
        with pytest.raises(PermissionError, match="remediation.history.view"):
            RudrixRemediationOperationsTool().execute(
                db=object(),
                arguments=_remediation_args(operation="HISTORY"),
            )
    finally:
        reset_rudrix_permissions(token)
