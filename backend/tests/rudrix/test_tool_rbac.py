from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai.authorization import (
    get_rudrix_permissions,
    permissions_for_user,
    reset_rudrix_permissions,
    set_rudrix_permissions,
)
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.base import BaseAITool
from app.ai.tools.registry import AIToolRegistry


class ProbeTool(BaseAITool):
    name = "list_integrations"
    description = "RBAC execution probe"
    parameters = {
        "type": "object",
        "properties": {},
    }

    def __init__(self):
        self.calls = 0

    def execute(self, *, db, arguments):
        self.calls += 1
        return {"ok": True}


def definition_names(registry) -> set[str]:
    return {
        definition["name"]
        for definition in registry.definitions()
    }


def test_integration_tools_are_hidden_without_integration_view():
    token = set_rudrix_permissions({"dashboard.view", "duplicate.view"})
    try:
        names = definition_names(create_ai_tool_registry())
    finally:
        reset_rudrix_permissions(token)

    assert "list_integrations" not in names
    assert "get_integration_details" not in names
    assert "get_dashboard_summary" in names
    assert "get_duplicate_summary" in names


def test_duplicate_tools_are_hidden_without_duplicate_view():
    token = set_rudrix_permissions({"integration.view"})
    try:
        names = definition_names(create_ai_tool_registry())
    finally:
        reset_rudrix_permissions(token)

    assert "list_integrations" in names
    assert "get_duplicate_summary" not in names
    assert "search_duplicate_groups" not in names
    assert "get_duplicate_group_details" not in names
    assert "get_review_statistics" not in names
    assert "get_confidence_breakdown" not in names


def test_operations_knowledge_and_ml_tools_use_their_service_permissions():
    token = set_rudrix_permissions({"operations.view", "knowledge.view"})
    try:
        names = definition_names(create_ai_tool_registry())
    finally:
        reset_rudrix_permissions(token)

    assert "get_operations_summary" in names
    assert "search_operations" in names
    assert "search_knowledge_base" in names
    assert "list_knowledge_documents" in names
    assert "get_training_label_summary" not in names


def test_unauthorized_execution_is_blocked_before_tool_runs():
    registry = AIToolRegistry()
    probe = ProbeTool()
    registry.register(probe)

    token = set_rudrix_permissions(set())
    try:
        with pytest.raises(PermissionError, match="Access denied"):
            registry.execute(
                name="list_integrations",
                db=object(),
                arguments={},
            )
    finally:
        reset_rudrix_permissions(token)

    assert probe.calls == 0


def test_authorized_execution_reaches_tool():
    registry = AIToolRegistry()
    probe = ProbeTool()
    registry.register(probe)

    token = set_rudrix_permissions({"integration.view"})
    try:
        result = registry.execute(
            name="list_integrations",
            db=object(),
            arguments={},
        )
    finally:
        reset_rudrix_permissions(token)

    assert result == {"ok": True}
    assert probe.calls == 1


def test_owner_permissions_are_unrestricted():
    owner = SimpleNamespace(
        role="OWNER",
        role_record=None,
    )

    assert permissions_for_user(owner) == frozenset({"*"})

    token = set_rudrix_permissions(permissions_for_user(owner))
    try:
        names = definition_names(create_ai_tool_registry())
    finally:
        reset_rudrix_permissions(token)

    assert "get_dashboard_summary" in names
    assert "list_integrations" in names
    assert "get_duplicate_summary" in names
    assert "get_operations_summary" in names
    assert "search_knowledge_base" in names
    assert "get_training_label_summary" in names


def test_normal_user_permissions_are_derived_from_role_record():
    role_record = SimpleNamespace(
        permissions=[
            SimpleNamespace(code="dashboard.view"),
            SimpleNamespace(code="duplicate.view"),
        ]
    )
    user = SimpleNamespace(
        role="USER",
        role_record=role_record,
    )

    permissions = permissions_for_user(user)

    assert permissions == frozenset({"dashboard.view", "duplicate.view"})


def test_permission_context_is_reset_cleanly():
    original = get_rudrix_permissions()
    token = set_rudrix_permissions({"integration.view"})

    assert get_rudrix_permissions() == frozenset({"integration.view"})

    reset_rudrix_permissions(token)

    assert get_rudrix_permissions() == original
