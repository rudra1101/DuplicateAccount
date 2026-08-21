from app.ai.duplicate_engine.hybrid_score import calculate_hybrid_score
from app.ai.duplicate_engine.normalizer import normalize_account
from app.ai.duplicate_engine.types import ComparisonFeatures


def _features(**overrides) -> ComparisonFeatures:
    values = {
        "username_similarity": 0.0,
        "display_name_similarity": 0.0,
        "first_name_similarity": 0.0,
        "last_name_similarity": 0.0,
        "email_similarity": 0.0,
        "email_local_similarity": 0.0,
        "manager_similarity": 0.0,
        "department_similarity": 0.0,
        "title_similarity": 0.0,
        "location_similarity": 0.0,
        "phone_similarity": 0.0,
        "identity_embedding_similarity": 0.0,
        "name_embedding_similarity": 0.0,
        "organization_embedding_similarity": 0.0,
        "employee_id_exact": False,
        "email_exact": False,
        "username_exact": False,
        "phone_exact": False,
        "department_exact": False,
        "manager_exact": False,
        "status_exact": False,
        "same_application": True,
        "account_1_missing_fields": 10,
        "account_2_missing_fields": 10,
    }
    values.update(overrides)
    return ComparisonFeatures(**values)


def test_normalizer_reads_dynamic_raw_attributes():
    account = normalize_account(
        {
            "application": "ISC",
            "username": "fallback-id",
            "rawAttributes": {
                "employeeNumber": "001234",
                "workEmail": "Jane.Doe@Example.COM",
                "givenName": "Jane",
                "sn": "Doe",
                "departmentName": "Security",
            },
        }
    )

    assert account.employee_id == "001234"
    assert account.email == "jane.doe@example.com"
    assert account.first_name == "jane"
    assert account.last_name == "doe"
    assert account.department == "security"


def test_same_application_is_not_penalized():
    same_app = calculate_hybrid_score(
        _features(
            username_similarity=0.94,
            display_name_similarity=0.96,
            first_name_similarity=1.0,
            last_name_similarity=1.0,
            same_application=True,
        )
    )
    different_app = calculate_hybrid_score(
        _features(
            username_similarity=0.94,
            display_name_similarity=0.96,
            first_name_similarity=1.0,
            last_name_similarity=1.0,
            same_application=False,
        )
    )

    assert same_app == different_app


def test_missing_optional_fields_do_not_reduce_strong_match():
    sparse = calculate_hybrid_score(
        _features(
            employee_id_exact=True,
            email_exact=True,
            display_name_similarity=0.96,
            first_name_similarity=1.0,
            last_name_similarity=1.0,
            account_1_missing_fields=10,
            account_2_missing_fields=10,
        )
    )
    complete = calculate_hybrid_score(
        _features(
            employee_id_exact=True,
            email_exact=True,
            display_name_similarity=0.96,
            first_name_similarity=1.0,
            last_name_similarity=1.0,
            account_1_missing_fields=0,
            account_2_missing_fields=0,
        )
    )

    assert sparse == complete
    assert sparse >= 97.0
