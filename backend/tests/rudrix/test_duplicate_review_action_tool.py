from __future__ import annotations

import pytest

from app.ai.agent_core.capabilities import CapabilityCatalog
from app.ai.authorization import (
    reset_rudrix_actor,
    reset_rudrix_permissions,
    set_rudrix_actor,
    set_rudrix_permissions,
)
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.duplicate_action_tools import ReviewDuplicateCandidateTool
from app.ai.tools.registry import TOOL_PERMISSION_MAP
import app.ai.tools.duplicate_action_tools as duplicate_action_tools


def test_duplicate_review_action_has_dedicated_capability_and_permission():
    registry = create_ai_tool_registry()
    definitions = {item["name"]: item for item in registry.definitions()}

    assert "review_duplicate_candidate" in definitions
    assert TOOL_PERMISSION_MAP["review_duplicate_candidate"] == "duplicate.review"

    capabilities = {
        capability.name: capability
        for capability in CapabilityCatalog(registry).capabilities()
    }
    action = capabilities["review_duplicate_candidate"]
    assert action.kind.value == "WRITE"
    assert action.domain == "duplicate"


def test_duplicate_review_action_schema_accepts_grounded_candidate_id():
    registry = create_ai_tool_registry()
    definition = next(
        item for item in registry.definitions()
        if item["name"] == "review_duplicate_candidate"
    )

    properties = definition["parameters"]["properties"]
    assert "candidate_id" in properties
    assert "decision" in properties
    assert set(definition["parameters"]["required"]) == {"candidate_id", "decision"}


def test_duplicate_review_action_requires_review_permission(monkeypatch):
    called = False

    def fake_save(**kwargs):
        nonlocal called
        called = True
        return kwargs

    monkeypatch.setattr(
        duplicate_action_tools,
        "save_duplicate_group_candidate_decision",
        fake_save,
    )
    token = set_rudrix_permissions({"duplicate.view"})
    try:
        with pytest.raises(PermissionError, match="duplicate.review"):
            ReviewDuplicateCandidateTool().execute(
                db=object(),
                arguments={"candidate_id": 9694, "decision": "DUPLICATE"},
            )
    finally:
        reset_rudrix_permissions(token)

    assert called is False


def test_duplicate_review_action_executes_grounded_candidate_for_authorized_actor(monkeypatch):
    captured = {}

    def fake_save(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(
        duplicate_action_tools,
        "save_duplicate_group_candidate_decision",
        fake_save,
    )
    permission_token = set_rudrix_permissions({"duplicate.view", "duplicate.review"})
    actor_token = set_rudrix_actor("Super Admin")
    try:
        result = ReviewDuplicateCandidateTool().execute(
            db=object(),
            arguments={
                "candidate_id": 9694,
                "decision": "DUPLICATE",
                "comment": "Confirmed from Rudrix conversation context.",
            },
        )
    finally:
        reset_rudrix_actor(actor_token)
        reset_rudrix_permissions(permission_token)

    assert captured["candidate_id"] == 9694
    assert captured["decision"] == "DUPLICATE"
    assert captured["reviewer_name"] == "Super Admin"
    assert result["candidateId"] == 9694
    assert result["decision"] == "DUPLICATE"
    assert "Marked candidate" in result["message"]
