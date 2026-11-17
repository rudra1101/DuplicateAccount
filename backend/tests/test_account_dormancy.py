from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
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
