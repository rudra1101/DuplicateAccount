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
from app.ai.tools.registry import (
    AIToolRegistry,
    TOOL_PERMISSION_MAP,
)


class ProbeTool(BaseAITool):
    name = "list_integrations"
    description = "RBAC execution probe"
    parameters = {"type": "object", "properties": {}}

    def __init__(self):
        self.calls = 0

    def execute(self, *, db, arguments):
        self.calls += 1
        return {"ok": True}


class UnmappedProbeTool(ProbeTool):
    name = "future_sensitive_tool"


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def first(self):
        return self.value


class RoleLookupDb:
    def __init__(self, role_record):
        self.role_record = role_record

    def scalars(self, statement):
        return ScalarResult(self.role_record)


def definition_names(registry) -> set[str]:
    return {definition["name"] for definition in registry.definitions()}


def test_every_registered_rudrix_tool_has_an_explicit_permission_mapping():
    names = definition_names(create_ai_tool_registry())
    assert names <= set(TOOL_PERMISSION_MAP)


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
            registry.execute(name="list_integrations", db=object(), arguments={})
    finally:
        reset_rudrix_permissions(token)

    assert probe.calls == 0


def test_authorized_execution_reaches_tool():
    registry = AIToolRegistry()
    probe = ProbeTool()
    registry.register(probe)

    token = set_rudrix_permissions({"integration.view"})
    try:
        result = registry.execute(name="list_integrations", db=object(), arguments={})
    finally:
        reset_rudrix_permissions(token)

    assert result == {"ok": True}
    assert probe.calls == 1


def test_unmapped_future_tool_is_hidden_and_blocked_fail_closed():
    registry = AIToolRegistry()
    probe = UnmappedProbeTool()
    registry.register(probe)

    token = set_rudrix_permissions({"*"})
    try:
        assert "future_sensitive_tool" not in definition_names(registry)
        with pytest.raises(PermissionError, match="Access denied"):
            registry.execute(name="future_sensitive_tool", db=object(), arguments={})
    finally:
        reset_rudrix_permissions(token)

    assert probe.calls == 0


def test_owner_permissions_are_unrestricted_for_mapped_tools():
    owner = SimpleNamespace(role="OWNER", role_record=None)
    assert permissions_for_user(owner) == frozenset({"*"})


def test_non_owner_roles_use_assigned_permissions_from_request_db():
    role_record = SimpleNamespace(
        permissions=[
            SimpleNamespace(code="remediation.view"),
            SimpleNamespace(code="report.view"),
        ]
    )
    user = SimpleNamespace(role="ADMIN", role_record=None)

    permissions = permissions_for_user(user, db=RoleLookupDb(role_record))

    assert permissions == frozenset({"remediation.view", "report.view"})

    token = set_rudrix_permissions(permissions)
    try:
        names = definition_names(create_ai_tool_registry())
    finally:
        reset_rudrix_permissions(token)

    assert "search_remediation_items" in names
    assert "generate_report" in names
    assert "create_remediation_ticket" not in names


def test_custom_role_with_remediation_manage_can_create_ticket():
    role_record = SimpleNamespace(
        permissions=[
            SimpleNamespace(code="remediation.view"),
            SimpleNamespace(code="remediation.manage"),
        ]
    )
    user = SimpleNamespace(role="REMEDIATION_ANALYST", role_record=None)
    permissions = permissions_for_user(user, db=RoleLookupDb(role_record))

    token = set_rudrix_permissions(permissions)
    try:
        names = definition_names(create_ai_tool_registry())
    finally:
        reset_rudrix_permissions(token)

    assert "search_remediation_items" in names
    assert "create_remediation_ticket" in names


def test_normal_user_permissions_are_derived_from_role_record_without_db():
    role_record = SimpleNamespace(
        permissions=[
            SimpleNamespace(code="dashboard.view"),
            SimpleNamespace(code="duplicate.view"),
        ]
    )
    user = SimpleNamespace(role="USER", role_record=role_record)

    permissions = permissions_for_user(user)
    assert permissions == frozenset({"dashboard.view", "duplicate.view"})


def test_permission_context_is_reset_cleanly():
    original = get_rudrix_permissions()
    token = set_rudrix_permissions({"integration.view"})

    assert get_rudrix_permissions() == frozenset({"integration.view"})

    reset_rudrix_permissions(token)
    assert get_rudrix_permissions() == original
