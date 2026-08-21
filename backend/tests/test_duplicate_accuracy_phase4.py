from app.ai.duplicate_engine.attribute_profiler import (
    AttributeCategory,
    profile_application_attributes,
)
from app.ai.duplicate_engine.normalizer import normalize_account


def _profiled_accounts():
    payloads = [
        {
            "id": "1",
            "application": "ISC",
            "username": "alpha.one",
            "rawAttributes": {
                "lastRefresh": "2026-08-20T10:00:00Z",
                "lifecycleState": {"stateName": "active"},
                "isManager": False,
                "payrollNumber": "P100",
            },
        },
        {
            "id": "2",
            "application": "ISC",
            "username": "alpha.duplicate",
            "rawAttributes": {
                "lastRefresh": "2026-08-20T10:00:00Z",
                "lifecycleState": {"stateName": "active"},
                "isManager": False,
                "payrollNumber": "P100",
            },
        },
        {
            "id": "3",
            "application": "ISC",
            "username": "beta.user",
            "rawAttributes": {
                "lastRefresh": "2026-08-21T11:00:00Z",
                "lifecycleState": {"stateName": "inactive"},
                "isManager": True,
                "payrollNumber": "P200",
            },
        },
        {
            "id": "4",
            "application": "ISC",
            "username": "gamma.user",
            "rawAttributes": {
                "lastRefresh": "2026-08-22T12:00:00Z",
                "lifecycleState": {"stateName": "active"},
                "isManager": False,
                "payrollNumber": "P300",
            },
        },
    ]
    return [normalize_account(payload) for payload in payloads]


def test_isc_refresh_timestamp_is_not_blocking_evidence():
    profiles = {
        profile.name: profile
        for profile in profile_application_attributes(_profiled_accounts())
    }

    assert profiles["lastRefresh"].category == AttributeCategory.DATE
    assert profiles["lastRefresh"].blocking_eligible is False


def test_isc_lifecycle_state_name_is_status_not_person_name():
    profiles = {
        profile.name: profile
        for profile in profile_application_attributes(_profiled_accounts())
    }

    assert profiles["lifecycleState.stateName"].category == AttributeCategory.STATUS
    assert profiles["lifecycleState.stateName"].blocking_eligible is False


def test_boolean_manager_flag_is_not_organizational_blocking_evidence():
    profiles = {
        profile.name: profile
        for profile in profile_application_attributes(_profiled_accounts())
    }

    assert profiles["isManager"].category == AttributeCategory.STATUS
    assert profiles["isManager"].blocking_eligible is False


def test_real_custom_identifier_remains_available_for_blocking():
    profiles = {
        profile.name: profile
        for profile in profile_application_attributes(_profiled_accounts())
    }

    assert profiles["payrollNumber"].category == AttributeCategory.IDENTIFIER
    assert profiles["payrollNumber"].blocking_eligible is True
