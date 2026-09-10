from app.db_models.account import AccountRecord
from app.db_models.correlation_policy import CorrelationPolicyRecord, CorrelationRuleRecord
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
        "raw_attributes": {"extensionAttribute10": "HR-1001"},
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
        "raw_attributes": {"workerReference": "HR-1001"},
    }
    payload.update(overrides)
    return IdentityRecord(**payload)


def _policy(*rules):
    policy = CorrelationPolicyRecord(
        id=1,
        account_integration_id=20,
        authoritative_integration_id=10,
        name="AD to HR",
        strategy="FIRST_MATCH_WINS",
        enabled=True,
    )
    policy.rules = [
        CorrelationRuleRecord(
            id=index,
            policy_id=1,
            priority=index,
            account_attribute=account_attribute,
            identity_attribute=identity_attribute,
            match_type=match_type,
            enabled=True,
        )
        for index, (account_attribute, identity_attribute, match_type) in enumerate(rules, start=1)
    ]
    return policy


def test_correlation_uses_user_rule_priority():
    employee_match = _identity(source_identity_id="employee-match")
    email_match = _identity(
        source_identity_id="email-match",
        employee_id="2000",
        email="rudra@example.com",
    )
    policy = _policy(
        ("email", "email", "CASE_INSENSITIVE"),
        ("employeeId", "employeeId", "EXACT"),
    )

    result = correlate_account(
        _account(),
        identities=[employee_match, email_match],
        policy=policy,
    )

    assert result.identity is email_match
    assert result.method == "email->email:CASE_INSENSITIVE"
    assert result.attempts[0]["result"] == "MATCHED"


def test_correlation_supports_dynamic_raw_attributes():
    identity = _identity()
    policy = _policy(("extensionAttribute10", "workerReference", "EXACT"))

    result = correlate_account(_account(), identities=[identity], policy=policy)

    assert result.identity is identity
    assert result.method == "extensionAttribute10->workerReference:EXACT"


def test_normalized_matching_is_configurable():
    identity = _identity(raw_attributes={"workerReference": "HR 1001"})
    account = _account(raw_attributes={"extensionAttribute10": "hr-1001"})
    policy = _policy(("extensionAttribute10", "workerReference", "NORMALIZED"))

    result = correlate_account(account, identities=[identity], policy=policy)

    assert result.identity is identity
    assert result.confidence == 95.0


def test_ambiguous_match_does_not_choose_identity():
    first = _identity(source_identity_id="one", employee_id="1001")
    second = _identity(source_identity_id="two", employee_id="1001")
    policy = _policy(("employeeId", "employeeId", "EXACT"))

    result = correlate_account(_account(), identities=[first, second], policy=policy)

    assert result.identity is None
    assert result.ambiguous is True
    assert result.attempts[0]["result"] == "AMBIGUOUS"


def test_unmatched_account_records_all_attempts():
    policy = _policy(
        ("employeeId", "employeeId", "EXACT"),
        ("email", "email", "CASE_INSENSITIVE"),
    )

    result = correlate_account(
        _account(employee_id="9999", email="missing@example.com"),
        identities=[_identity()],
        policy=policy,
    )

    assert result.identity is None
    assert result.method is None
    assert [attempt["result"] for attempt in result.attempts] == ["NO_MATCH", "NO_MATCH"]
