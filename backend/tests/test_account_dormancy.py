from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
from app.api.source_accounts import DormancyActionRequest, send_dormancy_reminder
from app.db_models.application_settings import ApplicationSettingsRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.source_account import SourceAccountRecord
from app.schemas.application_schema import ApplicationInput, SchemaAttributeInput
from app.services.account_dormancy_service import (
    DATE_FORMAT_AUTO,
    DATE_FORMAT_CUSTOM,
    DATE_FORMAT_ISO_8601,
    DATE_FORMAT_UNIX_MICROSECONDS,
    DATE_FORMAT_UNIX_MILLISECONDS,
    DATE_FORMAT_UNIX_NANOSECONDS,
    DATE_FORMAT_UNIX_SECONDS,
    DATE_FORMAT_WINDOWS_FILETIME,
    DormancyConfig,
    inactive_days,
    is_dormant,
    parse_last_login,
)
from app.services.service_desk_service import create_dormant_account_ticket
from app.services.source_account_inventory_service import (
    list_source_accounts,
    source_account_to_dict,
    upsert_source_accounts,
)


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _attribute(name: str) -> SchemaAttributeInput:
    return SchemaAttributeInput(name=name)


def _windows_filetime(value: datetime) -> int:
    epoch = datetime(1601, 1, 1, tzinfo=UTC)
    return int((value - epoch).total_seconds() * 10_000_000)


@pytest.mark.parametrize(
    ("date_format", "source_value"),
    [
        (DATE_FORMAT_UNIX_SECONDS, "1735689600"),
        (DATE_FORMAT_UNIX_MILLISECONDS, "1735689600000"),
        (DATE_FORMAT_UNIX_MICROSECONDS, "1735689600000000"),
        (DATE_FORMAT_UNIX_NANOSECONDS, "1735689600000000000"),
    ],
)
def test_parse_last_login_supports_unix_epoch_precisions(date_format, source_value):
    parsed = parse_last_login(source_value, date_format=date_format)

    assert parsed == datetime(2025, 1, 1, tzinfo=UTC)


def test_parse_last_login_supports_iso_8601():
    assert parse_last_login(
        "2025-01-01T10:15:30Z",
        date_format=DATE_FORMAT_ISO_8601,
    ) == datetime(2025, 1, 1, 10, 15, 30, tzinfo=UTC)


def test_parse_last_login_supports_windows_filetime_for_active_directory():
    expected = datetime(2025, 1, 1, 10, 15, 30, tzinfo=UTC)

    parsed = parse_last_login(
        str(_windows_filetime(expected)),
        date_format=DATE_FORMAT_WINDOWS_FILETIME,
    )

    assert parsed == expected


@pytest.mark.parametrize(
    ("custom_format", "source_value"),
    [
        ("%Y/%m/%d %H:%M:%S", "2025/01/02 03:04:05"),
        ("yyyy-MM-dd HH:mm:ss", "2025-01-02 03:04:05"),
    ],
)
def test_parse_last_login_supports_custom_formats(custom_format, source_value):
    parsed = parse_last_login(
        source_value,
        date_format=DATE_FORMAT_CUSTOM,
        custom_format=custom_format,
    )

    assert parsed == datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_auto_mode_recognizes_compact_calendar_value_before_epoch():
    assert parse_last_login(
        "20250102",
        date_format=DATE_FORMAT_AUTO,
    ) == datetime(2025, 1, 2, tzinfo=UTC)


def test_invalid_last_login_value_is_not_treated_as_dormant():
    assert parse_last_login("not-a-date", date_format=DATE_FORMAT_AUTO) is None


def test_application_requires_last_login_attribute_to_exist():
    with pytest.raises(ValueError, match="Last-login attribute must exist"):
        ApplicationInput(
            name="Active Directory",
            nativeIdentityAttribute="uid",
            lastLoginAttribute="lastLogonTimestamp",
            inactivityThresholdDays=90,
            attributes=[_attribute("uid")],
        )


def test_custom_date_format_requires_pattern():
    with pytest.raises(ValueError, match="custom last-login date format"):
        ApplicationInput(
            name="App",
            nativeIdentityAttribute="uid",
            lastLoginAttribute="last_login",
            lastLoginDateFormat="CUSTOM",
            inactivityThresholdDays=30,
            attributes=[_attribute("uid"), _attribute("last_login")],
        )


def test_last_login_tracking_requires_threshold():
    with pytest.raises(ValueError, match="Inactivity threshold days"):
        ApplicationInput(
            name="App",
            nativeIdentityAttribute="uid",
            lastLoginAttribute="last_login",
            inactivityThresholdDays=None,
            attributes=[_attribute("uid"), _attribute("last_login")],
        )


def test_aggregation_normalizes_configured_last_login_into_inventory():
    expected = datetime(2025, 1, 1, tzinfo=UTC)
    with _session() as db:
        integration = IntegrationRecord(
            name="AD",
            connector_type="LOCAL",
            configuration={
                "accountDormancyMappings": {
                    "Active Directory": {
                        "attribute": "lastLogonTimestamp",
                        "dateFormat": "WINDOWS_FILETIME",
                        "thresholdDays": 90,
                    }
                }
            },
            enabled=True,
        )
        db.add(integration)
        db.commit()
        db.refresh(integration)

        upsert_source_accounts(
            db,
            integration_id=integration.id,
            accounts=[
                {
                    "id": "alice",
                    "application": "Active Directory",
                    "username": "alice",
                    "email": "alice@example.com",
                    "status": "ACTIVE",
                    "rawAttributes": {
                        "uid": "alice",
                        "lastLogonTimestamp": str(_windows_filetime(expected)),
                    },
                }
            ],
            scan_id=None,
            aggregation_type="FULL",
        )

        account = db.scalar(
            select(SourceAccountRecord).where(
                SourceAccountRecord.integration_id == integration.id,
                SourceAccountRecord.native_identity == "alice",
            )
        )

        assert account is not None
        # SQLite may return a naive datetime even when timezone=True; compare the
        # source wall-clock value after normalizing the test side.
        assert account.last_login_at.replace(tzinfo=UTC) == expected


def test_dormant_query_uses_application_threshold_and_excludes_inactive_accounts():
    now = datetime.now(UTC)
    with _session() as db:
        integration = IntegrationRecord(
            name="Apps",
            connector_type="LOCAL",
            configuration={
                "accountDormancyMappings": {
                    "App A": {
                        "attribute": "last_login",
                        "dateFormat": "ISO_8601",
                        "thresholdDays": 90,
                    },
                    "App B": {
                        "attribute": "last_login",
                        "dateFormat": "ISO_8601",
                        "thresholdDays": 30,
                    },
                }
            },
            enabled=True,
        )
        db.add(integration)
        db.flush()

        rows = [
            SourceAccountRecord(
                integration_id=integration.id,
                application="App A",
                native_identity="old-a",
                status="ACTIVE",
                last_login_at=now - timedelta(days=120),
                raw_attributes={},
                attribute_fingerprint="a",
                active=True,
                deleted=False,
            ),
            SourceAccountRecord(
                integration_id=integration.id,
                application="App A",
                native_identity="recent-a",
                status="ACTIVE",
                last_login_at=now - timedelta(days=20),
                raw_attributes={},
                attribute_fingerprint="b",
                active=True,
                deleted=False,
            ),
            SourceAccountRecord(
                integration_id=integration.id,
                application="App B",
                native_identity="old-b",
                status="UNKNOWN",
                last_login_at=now - timedelta(days=45),
                raw_attributes={},
                attribute_fingerprint="c",
                active=True,
                deleted=False,
            ),
            SourceAccountRecord(
                integration_id=integration.id,
                application="App B",
                native_identity="disabled-b",
                status="INACTIVE",
                last_login_at=now - timedelta(days=200),
                raw_attributes={},
                attribute_fingerprint="d",
                active=True,
                deleted=False,
            ),
        ]
        db.add_all(rows)
        db.commit()

        dormant_rows, total = list_source_accounts(
            db,
            integration_id=integration.id,
            dormant=True,
            page=1,
            page_size=50,
        )

        assert total == 2
        assert {row.native_identity for row in dormant_rows} == {"old-a", "old-b"}


def test_dormancy_serializer_exposes_policy_and_action_state():
    config = DormancyConfig(
        attribute="last_login",
        date_format="ISO_8601",
        custom_format=None,
        threshold_days=30,
    )
    account = SourceAccountRecord(
        id=10,
        integration_id=1,
        application="App",
        native_identity="alice",
        status="ACTIVE",
        last_login_at=datetime.now(UTC) - timedelta(days=45),
        last_dormancy_reminder_at=datetime(2026, 1, 2, tzinfo=UTC),
        dormancy_ticket_id="INC001",
        dormancy_ticket_status="Open",
        raw_attributes={},
        attribute_fingerprint="fingerprint",
        active=True,
        deleted=False,
    )

    payload = source_account_to_dict(account, config)

    assert payload["dormant"] is True
    assert payload["dormancyThresholdDays"] == 30
    assert payload["inactiveDays"] >= 45
    assert payload["lastDormancyReminderAt"] is not None
    assert payload["dormancyTicketId"] == "INC001"
    assert is_dormant(account, config) is True
    assert inactive_days(account.last_login_at) >= 45



def test_dormancy_reminder_uses_system_email_and_records_timestamp(monkeypatch):
    sent: dict[str, object] = {}

    def fake_send_email(*, recipients, subject, text_body, html_body=None):
        sent["recipients"] = recipients
        sent["subject"] = subject
        sent["text_body"] = text_body
        sent["html_body"] = html_body

    monkeypatch.setattr("app.api.source_accounts.send_email", fake_send_email)

    with _session() as db:
        integration = IntegrationRecord(
            name="Dormancy Source",
            connector_type="LOCAL",
            configuration={
                "accountDormancyMappings": {
                    "App": {
                        "attribute": "last_login",
                        "dateFormat": "ISO_8601",
                        "thresholdDays": 30,
                    }
                }
            },
            enabled=True,
        )
        db.add(integration)
        db.flush()
        account = SourceAccountRecord(
            integration_id=integration.id,
            application="App",
            native_identity="alice",
            display_name="Alice <Admin>",
            username="alice",
            email="alice@example.com",
            status="ACTIVE",
            last_login_at=datetime.now(UTC) - timedelta(days=45),
            raw_attributes={},
            attribute_fingerprint="reminder",
            active=True,
            deleted=False,
        )
        db.add(account)
        db.commit()
        db.refresh(account)

        response = send_dormancy_reminder(
            integration.id,
            account.id,
            DormancyActionRequest(requestedBy="admin"),
            db,
            object(),
        )

        assert sent["recipients"] == ["alice@example.com"]
        assert "inactive App account" in str(sent["subject"])
        assert "45" in str(sent["text_body"])
        assert "Alice &lt;Admin&gt;" in str(sent["html_body"])
        assert response["recipient"] == "alice@example.com"
        assert response["requestedBy"] == "admin"
        assert account.last_dormancy_reminder_at is not None


def test_dormant_disable_ticket_posts_service_desk_request_and_persists_state(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id": "INC-DORMANT-001",
                "status": "Open",
                "url": "https://servicedesk.example/incidents/INC-DORMANT-001",
            }

    class FakeClient:
        def __init__(self, *, timeout, verify):
            captured["timeout"] = timeout
            captured["verify"] = verify

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, json, headers, auth):
            captured["url"] = url
            captured["payload"] = json
            captured["headers"] = headers
            captured["auth"] = auth
            return FakeResponse()

    monkeypatch.setattr("app.services.service_desk_service.httpx.Client", FakeClient)

    with _session() as db:
        integration = IntegrationRecord(
            name="Dormancy Source",
            connector_type="LOCAL",
            configuration={},
            enabled=True,
        )
        db.add(integration)
        db.flush()
        account = SourceAccountRecord(
            integration_id=integration.id,
            application="App",
            native_identity="alice",
            username="alice",
            email="alice@example.com",
            status="ACTIVE",
            last_login_at=datetime.now(UTC) - timedelta(days=60),
            raw_attributes={},
            attribute_fingerprint="ticket",
            active=True,
            deleted=False,
        )
        settings = ApplicationSettingsRecord(
            id=1,
            service_desk_enabled=True,
            service_desk_name="ServiceNow",
            service_desk_base_url="https://servicedesk.example",
            service_desk_auth_type="NONE",
            service_desk_create_path="/api/incidents",
            service_desk_status_path="/api/incidents/{ticket_id}",
            service_desk_ticket_id_field="id",
            service_desk_ticket_status_field="status",
            service_desk_ticket_url_field="url",
            service_desk_completed_statuses="resolved,closed",
            service_desk_payload_template=(
                '{"summary":"{{summary}}","description":"{{description}}",'
                '"action":"{{action}}","accountKey":"{{account_key}}",'
                '"application":"{{application}}","username":"{{username}}"}'
            ),
            service_desk_verify_tls=True,
        )
        db.add_all([account, settings])
        db.commit()
        db.refresh(account)

        response = create_dormant_account_ticket(
            db,
            account=account,
            inactive_days=60,
            threshold_days=30,
            requested_by="admin",
        )

        payload = captured["payload"]
        assert captured["url"] == "https://servicedesk.example/api/incidents"
        assert isinstance(payload, dict)
        assert payload["action"] == "DISABLE"
        assert payload["accountKey"] == "alice"
        assert payload["application"] == "App"
        assert "60 days" in payload["description"]
        assert response["ticketId"] == "INC-DORMANT-001"
        assert response["ticketStatus"] == "Open"
        assert account.dormancy_ticket_id == "INC-DORMANT-001"
        assert account.dormancy_ticket_status == "Open"
        assert account.dormancy_ticket_created_at is not None
