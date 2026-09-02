from __future__ import annotations

from app.api import chat_stream
from app.schemas.chat import ChatHistoryMessage, ChatRequest


CONFIRMATION_MESSAGE = """
I found the duplicate account and need your confirmation:
- Remediation Item ID: 1
- Integration Name: Active Directory
- Account 2: active directory:acti-d000553 (aisha.rao415)

If the information is correct, I will create a ticket for deleting the account 2.
Please respond with 'confirm' to proceed.
"""


def request(message: str = "confirm") -> ChatRequest:
    return ChatRequest(
        message=message,
        conversationId="conversation-1",
        history=[
            ChatHistoryMessage(
                role="user",
                content="Create a ticket to delete account 2 for Aisha.",
            ),
            ChatHistoryMessage(
                role="assistant",
                content=CONFIRMATION_MESSAGE,
            ),
        ],
    )


def test_confirmation_recovers_exact_ticket_context():
    arguments = chat_stream._ticket_confirmation_arguments(request())

    assert arguments == {
        "remediation_item_id": 1,
        "target": "ACCOUNT_2",
        "action": "DELETE",
    }


def test_confirmation_does_not_guess_without_prior_assistant_confirmation():
    payload = ChatRequest(
        message="confirm",
        history=[
            ChatHistoryMessage(
                role="assistant",
                content="Remediation Item ID: 1. Account 2 looks duplicated.",
            )
        ],
    )

    assert chat_stream._ticket_confirmation_arguments(payload) is None


def test_confirmation_requires_remediation_manage(monkeypatch):
    called = False

    def should_not_create(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("ticket creation must not run")

    monkeypatch.setattr(chat_stream, "create_ticket", should_not_create)

    response = chat_stream._ticket_confirmation_response(
        db=object(),
        payload=request(),
        conversation_id="conversation-1",
        permissions=frozenset({"remediation.view"}),
    )

    assert response is not None
    assert "remediation.manage" in response.message
    assert called is False


def test_confirmation_creates_ticket_for_authorized_user(monkeypatch):
    captured = {}

    def fake_create_ticket(db, *, item_id, target, action, requested_by):
        captured.update(
            {
                "db": db,
                "item_id": item_id,
                "target": target,
                "action": action,
                "requested_by": requested_by,
            }
        )
        return {
            "ticketId": "INC001234",
            "targetAccountKey": "active directory:acti-d000553",
            "ticketUrl": "https://servicedesk.example/INC001234",
        }

    monkeypatch.setattr(chat_stream, "create_ticket", fake_create_ticket)
    fake_db = object()

    response = chat_stream._ticket_confirmation_response(
        db=fake_db,
        payload=request("yes"),
        conversation_id="conversation-1",
        permissions=frozenset({"remediation.view", "remediation.manage"}),
    )

    assert response is not None
    assert "INC001234" in response.message
    assert captured == {
        "db": fake_db,
        "item_id": 1,
        "target": "ACCOUNT_2",
        "action": "DELETE",
        "requested_by": "Rudrix",
    }
    assert response.toolsUsed[0].name == "create_remediation_ticket"
