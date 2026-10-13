from __future__ import annotations

from app.ai.tools.orphan_tools import SearchOrphanAccountsTool


def _neha_item():
    return {
        "orphanStateId": 108,
        "sourceAccountId": 208,
        "integrationId": 12,
        "integrationName": "Active Directory",
        "connectorType": "LOCAL",
        "application": "Active Directory",
        "nativeIdentity": "nverma",
        "username": "nverma",
        "displayName": "Neha Verma",
        "email": "neha.verma@example.com",
        "employeeId": "W90008",
        "orphaned": True,
        "orphanType": "UNMATCHED_ACCOUNT",
        "orphanStatus": "OPEN",
        "reason": "No configured correlation rule matched an authoritative identity.",
        "correlationAttempts": [],
    }


def test_named_orphan_misbound_to_reason_is_recovered_as_account_search(monkeypatch):
    calls = []

    def fake_list_orphans(_db, **kwargs):
        calls.append(dict(kwargs))
        if (
            kwargs.get("integration_name") == "Active Directory"
            and kwargs.get("reason") is None
            and kwargs.get("search") == "Neha Verma"
        ):
            return [_neha_item()]
        return []

    monkeypatch.setattr(
        "app.ai.tools.orphan_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    result = SearchOrphanAccountsTool().execute(
        db=object(),
        arguments={
            "integration": "Active Directory",
            "reason": "Neha Verma",
        },
    )

    assert result["count"] == 1
    assert result["items"][0]["displayName"] == "Neha Verma"
    assert result["reportFilters"]["integrationId"] == 12
    assert result["reportFilters"]["search"] == "Neha Verma"
    assert calls[0]["reason"] == "Neha Verma"
    assert any(
        call.get("reason") is None and call.get("search") == "Neha Verma"
        for call in calls[1:]
    )


def test_full_named_question_survives_an_extra_misbound_reason(monkeypatch):
    def fake_list_orphans(_db, **kwargs):
        if (
            kwargs.get("reason") is None
            and kwargs.get("search") == "why neha verma is orphan?"
        ):
            return [_neha_item()]
        return []

    monkeypatch.setattr(
        "app.ai.tools.orphan_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    result = SearchOrphanAccountsTool().execute(
        db=object(),
        arguments={
            "integration": "Active Directory",
            "search": "why neha verma is orphan?",
            "reason": "Neha Verma",
        },
    )

    assert result["count"] == 1
    assert result["items"][0]["employeeId"] == "W90008"
    assert result["reportFilters"]["search"] == "why neha verma is orphan?"


def test_real_correlation_reason_is_not_rebound_to_an_account_reference(monkeypatch):
    calls = []

    def fake_list_orphans(_db, **kwargs):
        calls.append(dict(kwargs))
        # Simulate lexical search finding a row because the reason text is part of
        # orphan evidence. The recovery guard must still reject it because the text
        # does not name any account identifier in the returned row.
        if (
            kwargs.get("reason") is None
            and kwargs.get("search")
            == "No configured correlation rule matched an authoritative identity."
        ):
            return [_neha_item()]
        return []

    monkeypatch.setattr(
        "app.ai.tools.orphan_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    result = SearchOrphanAccountsTool().execute(
        db=object(),
        arguments={
            "integration": "Active Directory",
            "reason": "No configured correlation rule matched an authoritative identity.",
        },
    )

    assert result["count"] == 0
    assert result["items"] == []
    assert calls[0]["reason"] == (
        "No configured correlation rule matched an authoritative identity."
    )


def test_source_name_is_not_rebound_as_an_account_reference(monkeypatch):
    def fake_list_orphans(_db, **kwargs):
        if kwargs.get("search") == "Active Directory":
            return [_neha_item()]
        return []

    monkeypatch.setattr(
        "app.ai.tools.orphan_tools.list_orphan_accounts",
        fake_list_orphans,
    )

    result = SearchOrphanAccountsTool().execute(
        db=object(),
        arguments={"integration": "Active Directory"},
    )

    assert result["count"] == 0
    assert result["items"] == []
