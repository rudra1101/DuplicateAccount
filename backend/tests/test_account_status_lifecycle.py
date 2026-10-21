import io

import pytest

from app.schemas.application_schema import ApplicationInput, SchemaAttributeInput
from app.services.account_loader import load_uploaded_accounts
from app.services.account_status_service import (
    ACCOUNT_STATE_ACTIVE,
    ACCOUNT_STATE_INACTIVE,
    ACCOUNT_STATE_UNKNOWN,
    account_is_duplicate_eligible,
    canonical_account_state,
    duplicate_eligible_accounts,
)


def _attribute(name: str) -> SchemaAttributeInput:
    return SchemaAttributeInput(name=name)


def test_configured_status_attribute_normalizes_source_value_and_preserves_raw_value():
    content = (
        b"application,uid,userState,displayName\n"
        b"Active Directory,a1,ENABLED,Alice Smith\n"
        b"Active Directory,a2,DISABLED,Alice Smith\n"
    )

    records = load_uploaded_accounts(
        io.BytesIO(content),
        allow_dynamic_schema=True,
        native_identity_attributes={"Active Directory": "uid"},
        status_mappings={
            "Active Directory": {
                "attribute": "userState",
                "activeValues": ["enabled"],
                "inactiveValues": ["disabled"],
            }
        },
    )

    assert [record.status for record in records] == [
        ACCOUNT_STATE_ACTIVE,
        ACCOUNT_STATE_INACTIVE,
    ]
    assert records[1].rawAttributes["userState"] == "DISABLED"


def test_status_mapping_is_case_insensitive_for_attribute_and_values():
    content = b"application,uid,AccountEnabled\nAD,one,FALSE\n"

    [record] = load_uploaded_accounts(
        io.BytesIO(content),
        allow_dynamic_schema=True,
        native_identity_attributes={"AD": "uid"},
        status_mappings={
            "ad": {
                "attribute": "accountenabled",
                "activeValues": ["TRUE"],
                "inactiveValues": ["false"],
            }
        },
    )

    assert record.status == ACCOUNT_STATE_INACTIVE


def test_unknown_status_remains_duplicate_eligible_for_backward_compatibility():
    assert canonical_account_state("custom-state") == ACCOUNT_STATE_UNKNOWN
    assert account_is_duplicate_eligible(ACCOUNT_STATE_ACTIVE) is True
    assert account_is_duplicate_eligible(ACCOUNT_STATE_UNKNOWN) is True
    assert account_is_duplicate_eligible(ACCOUNT_STATE_INACTIVE) is False


def test_inactive_account_is_kept_in_collection_but_removed_from_duplicate_candidates():
    content = (
        b"application,uid,enabled,displayName,email\n"
        b"AD,active-1,true,John Smith,john@example.com\n"
        b"AD,disabled-1,false,John Smith,john@example.com\n"
    )

    records = load_uploaded_accounts(
        io.BytesIO(content),
        allow_dynamic_schema=True,
        native_identity_attributes={"AD": "uid"},
        status_mappings={
            "AD": {
                "attribute": "enabled",
                "activeValues": ["true"],
                "inactiveValues": ["false"],
            }
        },
    )

    eligible = duplicate_eligible_accounts(records)

    assert len(records) == 2
    assert records[1].status == ACCOUNT_STATE_INACTIVE
    assert [account.id for account in eligible] == ["active-1"]


def test_status_attribute_must_exist_in_application_schema():
    with pytest.raises(ValueError, match="Status attribute must exist"):
        ApplicationInput(
            name="Active Directory",
            nativeIdentityAttribute="uid",
            statusAttribute="accountEnabled",
            attributes=[_attribute("uid")],
        )


def test_active_and_inactive_status_values_cannot_overlap():
    with pytest.raises(ValueError, match="cannot overlap"):
        ApplicationInput(
            name="Active Directory",
            nativeIdentityAttribute="uid",
            statusAttribute="accountEnabled",
            activeStatusValues=["true", "enabled"],
            inactiveStatusValues=["TRUE", "disabled"],
            attributes=[_attribute("uid"), _attribute("accountEnabled")],
        )
