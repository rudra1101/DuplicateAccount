from io import BytesIO

from app.services.account_loader import load_uploaded_accounts


def test_configured_native_identity_keeps_same_employee_accounts_distinct():
    content = b"objectGUID,sAMAccountName,employeeID,mail\nguid-1,rshankar,W00001,rudra@example.com\nguid-2,rshankar.legacy,W00001,rudra@example.com\n"

    accounts = load_uploaded_accounts(
        BytesIO(content),
        default_application="Active Directory",
        allow_dynamic_schema=True,
        native_identity_attributes={"Active Directory": "objectGUID"},
    )

    assert len(accounts) == 2
    assert accounts[0].id == "guid-1"
    assert accounts[1].id == "guid-2"
    assert accounts[0].employeeId == accounts[1].employeeId == "W00001"


def test_dynamic_feed_does_not_use_employee_id_as_native_identity_fallback():
    content = b"sAMAccountName,employeeID,mail\nrshankar,W00001,rudra@example.com\nrshankar.legacy,W00001,rudra@example.com\n"

    accounts = load_uploaded_accounts(
        BytesIO(content),
        default_application="Active Directory",
        allow_dynamic_schema=True,
    )

    assert len(accounts) == 2
    assert accounts[0].id != accounts[1].id
    assert accounts[0].id != "W00001"
    assert accounts[1].id != "W00001"
