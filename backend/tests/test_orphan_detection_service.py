from app.db_models.account import AccountRecord
from app.db_models.identity import IdentityRecord
from app.services.orphan_detection_service import correlate_account


def _account(**overrides):
    payload = {
        "scan_id": 1,
        "application": "Active Directory",
        "username": "rshankar",
        "display_name": "Rudra Shankar",
        "email": "rudra@example.com",
        "employee_id": "1001",
    }
    payload.update(overrides)
    return AccountRecord(**payload)


def _identity(**overrides):
    payload = {
        "integration_id": 10,
        "source_identity_id": "1001",
        "employee_id": "1001",
        "username": "rudra.hr",
        "email": "rudra.hr@example.com",
        "employment_status": "ACTIVE",
    }
    payload.update(overrides)
    return IdentityRecord(**payload)


def test_correlation_prefers_employee_id():
    identity = _identity()
    result = correlate_account(
        _account(),
        employee_index={"1001": identity},
        email_index={"rudra@example.com": _identity(source_identity_id="other")},
        username_index={},
    )

    assert result.identity is identity
    assert result.method == "EMPLOYEE_ID_EXACT"


def test_correlation_falls_back_to_email():
    identity = _identity(employee_id="2000", email="rudra@example.com")
    result = correlate_account(
        _account(employee_id=None),
        employee_index={},
        email_index={"rudra@example.com": identity},
        username_index={},
    )

    assert result.identity is identity
    assert result.method == "EMAIL_EXACT"


def test_correlation_falls_back_to_username():
    identity = _identity(employee_id="2000", email="other@example.com", username="rshankar")
    result = correlate_account(
        _account(employee_id=None, email=""),
        employee_index={},
        email_index={},
        username_index={"rshankar": identity},
    )

    assert result.identity is identity
    assert result.method == "USERNAME_EXACT"


def test_unmatched_account_returns_no_identity():
    result = correlate_account(
        _account(employee_id="9999", email="missing@example.com", username="missing"),
        employee_index={},
        email_index={},
        username_index={},
    )

    assert result.identity is None
    assert result.method is None
