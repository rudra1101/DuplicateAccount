from __future__ import annotations

from types import SimpleNamespace

from app.ai.agent_core.capabilities import CapabilityCatalog
from app.ai.agent_core.models import AgentState, CapabilityKind
from app.ai.agent_core.state import reduce_tool_result
from app.ai.authorization import (
    reset_rudrix_actor,
    reset_rudrix_permissions,
    set_rudrix_actor,
    set_rudrix_permissions,
)
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.orphan_remediation_tools import CreateOrphanRemediationTicketTool
from app.schemas.chat import ChatResponse, ToolInvocationResponse
from app.services.orphan_remediation_service import create_orphan_ticket


def _orphan_item() -> dict:
    return {
        "orphanStateId": 77,
        "sourceAccountId": 208,
        "integrationId": 12,
        "integrationName": "Active Directory",
        "application": "Active Directory",
        "displayName": "Neha Verma",
        "username": "nverma",
        "employeeId": "W90008",
        "nativeIdentity": "CN=Neha Verma,OU=Users,DC=example,DC=com",
        "orphanType": "UNMATCHED_ACCOUNT",
        "orphanStatus": "OPEN",
        "reason": "No configured correlation rule matched an authoritative identity.",
    }


def test_orphan_ticket_capability_requires_remediation_manage():
    token = set_rudrix_permissions({"integration.view", "remediation.view"})
    try:
        names = {item["name"] for item in create_ai_tool_registry().definitions()}
    finally:
        reset_rudrix_permissions(token)

    assert "create_orphan_remediation_ticket" not in names


def test_orphan_ticket_capability_is_write_and_exposed_when_authorized():
    token = set_rudrix_permissions(
        {"integration.view", "remediation.view", "remediation.manage"}
    )
    try:
        registry = create_ai_tool_registry()
        names = {item["name"] for item in registry.definitions()}
        capabilities = {item.name: item for item in CapabilityCatalog(registry).capabilities()}
    finally:
        reset_rudrix_permissions(token)

    assert "create_orphan_remediation_ticket" in names
    assert capabilities["create_orphan_remediation_ticket"].kind == CapabilityKind.WRITE


def test_named_orphan_ticket_preparation_requires_explicit_action(monkeypatch):
    monkeypatch.setattr(
        "app.ai.tools.orphan_remediation_tools.list_orphan_accounts",
        lambda _db, **_kwargs: [_orphan_item()],
    )

    def should_not_create(*_args, **_kwargs):
        raise AssertionError("Ticket creation must not run before the action is explicit.")

    monkeypatch.setattr(
        "app.ai.tools.orphan_remediation_tools.create_orphan_ticket",
        should_not_create,
    )

    result = CreateOrphanRemediationTicketTool().execute(
        db=object(),
        arguments={"reference": "Neha Verma", "action": None},
    )

    assert result["created"] is False
    assert result["requiresInput"] is True
    assert result["missingFields"] == ["action"]
    assert result["sourceAccountId"] == 208
    assert "DISABLE" in result["message"]
    assert "DELETE" in result["message"]


def test_orphan_ticket_creation_uses_grounded_account_and_authenticated_actor(monkeypatch):
    monkeypatch.setattr(
        "app.ai.tools.orphan_remediation_tools.list_orphan_accounts",
        lambda _db, **_kwargs: [_orphan_item()],
    )
    captured = {}

    def fake_create(_db, *, source_account_id, action, requested_by):
        captured.update(
            {
                "source_account_id": source_account_id,
                "action": action,
                "requested_by": requested_by,
            }
        )
        return {
            "created": True,
            "sourceAccountId": source_account_id,
            "application": "Active Directory",
            "displayName": "Neha Verma",
            "username": "nverma",
            "employeeId": "W90008",
            "orphanType": "UNMATCHED_ACCOUNT",
            "orphanStatus": "OPEN",
            "remediationAction": action,
            "ticketId": "INC001234",
            "ticketStatus": "CREATED",
            "ticketUrl": "https://servicedesk.example/tickets/INC001234",
        }

    monkeypatch.setattr(
        "app.ai.tools.orphan_remediation_tools.create_orphan_ticket",
        fake_create,
    )

    actor_token = set_rudrix_actor("admin@example.com")
    try:
        result = CreateOrphanRemediationTicketTool().execute(
            db=object(),
            arguments={"source_account_id": 208, "action": "DISABLE"},
        )
    finally:
        reset_rudrix_actor(actor_token)

    assert captured == {
        "source_account_id": 208,
        "action": "DISABLE",
        "requested_by": "admin@example.com",
    }
    assert result["created"] is True
    assert result["ticketId"] == "INC001234"
    assert "Open ticket" in result["message"]
    assert result["clientAction"]["type"] == "OPEN_EXTERNAL"


def test_orphan_ticket_response_keeps_real_ticket_link_authoritative():
    message = (
        "Created Service Desk ticket **INC001234** to **disable** orphan account "
        "**Neha Verma**. [Open ticket](https://servicedesk.example/tickets/INC001234)"
    )
    response = ChatResponse(
        conversationId="conversation-orphan-ticket",
        message="The requested remediation has been processed.",
        model="llama3.1:8b",
        toolsUsed=[
            ToolInvocationResponse(
                name="create_orphan_remediation_ticket",
                arguments={"source_account_id": 208, "action": "DISABLE"},
                result={
                    "success": True,
                    "data": {
                        "resultType": "orphan_remediation_ticket",
                        "created": True,
                        "sourceAccountId": 208,
                        "ticketId": "INC001234",
                        "ticketUrl": "https://servicedesk.example/tickets/INC001234",
                        "message": message,
                    },
                },
            )
        ],
        sources=[],
    )

    assert response.message == message
    assert "[Open ticket]" in response.message


def test_orphan_ticket_preparation_persists_pending_action_context():
    updated = reduce_tool_result(
        AgentState(),
        tool_name="create_orphan_remediation_ticket",
        tool_result={
            "success": True,
            "data": {
                "resultType": "orphan_remediation_ticket",
                "created": False,
                "requiresInput": True,
                "missingFields": ["action"],
                "sourceAccountId": 208,
                "account": _orphan_item(),
                "message": "Choose DISABLE or DELETE.",
            },
        },
    )

    assert updated.current_account is not None
    assert updated.current_account.id == 208
    assert updated.current_account.label == "Neha Verma"
    assert updated.pending_action is not None
    assert updated.pending_action.capability == "create_orphan_remediation_ticket"
    assert updated.pending_action.arguments["source_account_id"] == 208
    assert updated.pending_action.missing_fields == ["action"]


def test_successful_orphan_ticket_clears_pending_action():
    pending_state = reduce_tool_result(
        AgentState(),
        tool_name="create_orphan_remediation_ticket",
        tool_result={
            "success": True,
            "data": {
                "created": False,
                "requiresInput": True,
                "missingFields": ["action"],
                "sourceAccountId": 208,
                "account": _orphan_item(),
            },
        },
    )

    updated = reduce_tool_result(
        pending_state,
        tool_name="create_orphan_remediation_ticket",
        tool_result={
            "success": True,
            "data": {
                "created": True,
                "sourceAccountId": 208,
                "displayName": "Neha Verma",
                "username": "nverma",
                "application": "Active Directory",
                "orphanType": "UNMATCHED_ACCOUNT",
                "orphanStatus": "OPEN",
                "remediationAction": "DISABLE",
                "ticketId": "INC001234",
                "ticketStatus": "CREATED",
            },
        },
    )

    assert updated.pending_action is None
    assert updated.current_account is not None
    assert updated.current_account.attributes["ticketId"] == "INC001234"


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "id": "INC009999",
            "status": "new",
            "url": "https://servicedesk.example/tickets/INC009999",
        }


class _FakeHttpClient:
    def __init__(self, *args, **kwargs):
        self.posted = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, *, json, headers, auth):
        self.posted = {"url": url, "json": json, "headers": headers, "auth": auth}
        return _FakeResponse()


class _FakeDb:
    def __init__(self, orphan, account):
        self.orphan = orphan
        self.account = account
        self.commits = 0

    def scalar(self, _statement):
        return self.orphan

    def get(self, model, _record_id):
        return self.account

    def commit(self):
        self.commits += 1

    def refresh(self, _record):
        return None


def test_orphan_ticket_service_persists_ticket_without_resolving_orphan(monkeypatch):
    orphan = SimpleNamespace(
        id=77,
        integration_id=12,
        source_account_id=208,
        orphan_type="UNMATCHED_ACCOUNT",
        status="OPEN",
        active=True,
        evidence={"reason": "No configured correlation rule matched an authoritative identity."},
        remediation_action=None,
        actioned_by=None,
        service_desk_ticket_id=None,
        service_desk_ticket_status=None,
        service_desk_ticket_url=None,
        ticket_created_at=None,
        ticket_last_synced_at=None,
        ticket_error=None,
        updated_at=None,
    )
    account = SimpleNamespace(
        id=208,
        application="Active Directory",
        native_identity="CN=Neha Verma,OU=Users,DC=example,DC=com",
        display_name="Neha Verma",
        username="nverma",
        email="neha@example.com",
        employee_id="W90008",
    )
    db = _FakeDb(orphan, account)
    config = SimpleNamespace(
        enabled=True,
        name="ServiceNow",
        base_url="https://servicedesk.example",
        create_path="/tickets",
        ticket_id_field="id",
        ticket_status_field="status",
        ticket_url_field="url",
        payload_template=(
            '{"summary":"{{summary}}","description":"{{description}}",'
            '"action":"{{action}}","accountKey":"{{account_key}}",'
            '"application":"{{application}}"}'
        ),
        verify_tls=True,
        auth_type="NONE",
        username="",
        secret="",
    )

    monkeypatch.setattr(
        "app.services.orphan_remediation_service._config_from_db",
        lambda _db: config,
    )
    monkeypatch.setattr(
        "app.services.orphan_remediation_service.httpx.Client",
        _FakeHttpClient,
    )

    result = create_orphan_ticket(
        db,
        source_account_id=208,
        action="DISABLE",
        requested_by="admin@example.com",
    )

    assert result["ticketId"] == "INC009999"
    assert result["remediationAction"] == "DISABLE"
    assert orphan.service_desk_ticket_id == "INC009999"
    assert orphan.status == "OPEN"
    assert orphan.active is True
    assert db.commits == 1
