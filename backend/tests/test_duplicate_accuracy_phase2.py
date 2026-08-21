from app.ai.blocking import BlockingCandidateGenerator
from app.ai.duplicate_engine.attribute_profiler import (
    AttributeCategory,
    profile_application_attributes,
)
from app.ai.duplicate_engine.normalizer import normalize_account


def _account(account_id: str, username: str, payroll_number: str, guid: str):
    return normalize_account(
        {
            "id": account_id,
            "application": "ISC",
            "username": username,
            "rawAttributes": {
                "payrollNumber": payroll_number,
                "customGuid": guid,
            },
        }
    )


def test_profiler_classifies_custom_identifier_and_technical_key():
    accounts = [
        _account("1", "alpha.one", "P100", "g-1"),
        _account("2", "beta.two", "P100", "g-2"),
        _account("3", "gamma.three", "P200", "g-3"),
    ]

    profiles = {profile.name: profile for profile in profile_application_attributes(accounts)}

    assert profiles["payrollNumber"].category == AttributeCategory.IDENTIFIER
    assert profiles["payrollNumber"].blocking_eligible is True
    assert profiles["customGuid"].category == AttributeCategory.SOURCE_KEY
    assert profiles["customGuid"].blocking_eligible is False


def test_dynamic_profile_can_create_candidate_pair_without_legacy_similarity():
    accounts = [
        _account("1", "alpha.one", "P100", "g-1"),
        _account("2", "totally.different", "P100", "g-2"),
        _account("3", "third.account", "P200", "g-3"),
    ]

    generator = BlockingCandidateGenerator(
        minimum_blocking_score=4.0,
        max_candidates_per_account=10,
    )

    candidates = generator.generate(accounts)

    pairs = {
        (candidate.account_1.account_id, candidate.account_2.account_id)
        for candidate in candidates
    }

    assert ("1", "2") in pairs
    matched = next(
        candidate
        for candidate in candidates
        if (candidate.account_1.account_id, candidate.account_2.account_id) == ("1", "2")
    )
    assert any("payrollNumber" in reason for reason in matched.reasons)


def test_low_value_status_attribute_is_not_used_for_dynamic_blocking():
    accounts = [
        normalize_account(
            {
                "id": str(index),
                "application": "ISC",
                "username": f"user{index}",
                "rawAttributes": {"cloudLifecycleState": "active"},
            }
        )
        for index in range(1, 5)
    ]

    profiles = {profile.name: profile for profile in profile_application_attributes(accounts)}

    assert profiles["cloudLifecycleState"].category == AttributeCategory.STATUS
    assert profiles["cloudLifecycleState"].blocking_eligible is False
