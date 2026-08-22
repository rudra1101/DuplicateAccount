from app.ai.duplicate_engine.hybrid_score import calculate_hybrid_score
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
        "account_1_missing_fields": 0,
        "account_2_missing_fields": 0,
    }
    values.update(overrides)
    return ComparisonFeatures(**values)


def test_correlated_fuzzy_name_username_email_local_stays_out_of_auto_group_confidence():
    confidence = calculate_hybrid_score(
        _features(
            username_similarity=0.95,
            display_name_similarity=0.96,
            first_name_similarity=1.0,
            last_name_similarity=1.0,
            email_similarity=0.938,
            email_local_similarity=0.96,
        )
    )

    assert confidence <= 54.0


def test_email_local_similarity_does_not_stack_on_top_of_username_similarity():
    username_only = calculate_hybrid_score(
        _features(
            username_similarity=0.95,
            display_name_similarity=0.96,
        )
    )
    with_email_local = calculate_hybrid_score(
        _features(
            username_similarity=0.95,
            display_name_similarity=0.96,
            email_local_similarity=0.97,
            email_similarity=0.94,
        )
    )

    assert with_email_local <= 54.0
    assert with_email_local - username_only < 5.0


def test_exact_email_with_strong_name_keeps_high_confidence_floor():
    confidence = calculate_hybrid_score(
        _features(
            email_exact=True,
            display_name_similarity=0.96,
            first_name_similarity=1.0,
            last_name_similarity=1.0,
            username_similarity=0.94,
        )
    )

    assert confidence >= 87.0


def test_employee_id_and_exact_email_with_strong_name_remains_very_high():
    confidence = calculate_hybrid_score(
        _features(
            employee_id_exact=True,
            email_exact=True,
            display_name_similarity=0.96,
            first_name_similarity=1.0,
            last_name_similarity=1.0,
        )
    )

    assert confidence >= 97.0
