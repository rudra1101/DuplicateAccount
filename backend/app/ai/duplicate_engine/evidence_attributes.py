from __future__ import annotations

from typing import Any

from app.ai.duplicate_engine.types import DuplicatePrediction


def _has_value(account: Any, attribute_name: str) -> bool:
    value = getattr(account, attribute_name, None)
    return bool(str(value or "").strip())


def _both_have_value(
    prediction: DuplicatePrediction,
    attribute_name: str,
) -> bool:
    return (
        _has_value(prediction.account_1, attribute_name)
        and _has_value(prediction.account_2, attribute_name)
    )


def build_matched_attributes(
    prediction: DuplicatePrediction,
) -> list[str]:
    """
    Build candidate-specific evidence labels.

    Similarity percentages make candidates with the same broad evidence
    pattern distinguishable in the UI.
    """
    features = prediction.features
    matched: list[str] = []

    if (
        _both_have_value(prediction, "employee_id")
        and features.employee_id_exact
    ):
        matched.append("Employee ID Exact")

    if (
        _both_have_value(prediction, "email")
        and features.email_exact
    ):
        matched.append("Email Exact")
    elif (
        _both_have_value(prediction, "email")
        and features.email_similarity >= 0.80
    ):
        matched.append(
            f"Email Similarity ({features.email_similarity * 100:.1f}%)"
        )

    if (
        _both_have_value(prediction, "username")
        and features.username_exact
    ):
        matched.append("Username Exact")
    elif (
        _both_have_value(prediction, "username")
        and features.username_similarity >= 0.80
    ):
        matched.append(
            f"Username Similarity ({features.username_similarity * 100:.1f}%)"
        )

    if (
        _both_have_value(prediction, "display_name")
        and features.display_name_similarity >= 0.80
    ):
        matched.append(
            f"Display Name Similarity "
            f"({features.display_name_similarity * 100:.1f}%)"
        )

    if (
        _both_have_value(prediction, "first_name")
        and features.first_name_similarity >= 0.80
    ):
        matched.append(
            f"First Name Similarity "
            f"({features.first_name_similarity * 100:.1f}%)"
        )

    if (
        _both_have_value(prediction, "last_name")
        and features.last_name_similarity >= 0.80
    ):
        matched.append(
            f"Last Name Similarity "
            f"({features.last_name_similarity * 100:.1f}%)"
        )

    if (
        _both_have_value(prediction, "phone")
        and features.phone_exact
    ):
        matched.append("Phone Exact")

    if (
        _both_have_value(prediction, "department")
        and features.department_exact
    ):
        matched.append("Department Exact")

    if (
        _both_have_value(prediction, "manager")
        and features.manager_exact
    ):
        matched.append("Manager Exact")

    if (
        _both_have_value(prediction, "status")
        and features.status_exact
    ):
        matched.append("Status Exact")

    if (
        _both_have_value(prediction, "job_title")
        and features.title_similarity >= 0.80
    ):
        matched.append(
            f"Job Title Similarity ({features.title_similarity * 100:.1f}%)"
        )

    if (
        _both_have_value(prediction, "location")
        and features.location_similarity >= 0.80
    ):
        matched.append(
            f"Location Similarity ({features.location_similarity * 100:.1f}%)"
        )

    return matched


def build_different_attributes(
    prediction: DuplicatePrediction,
) -> list[str]:
    features = prediction.features
    different: list[str] = []

    if (
        _both_have_value(prediction, "employee_id")
        and not features.employee_id_exact
    ):
        different.append("Employee ID")

    if (
        _both_have_value(prediction, "email")
        and not features.email_exact
        and features.email_similarity < 0.80
    ):
        different.append("Email")

    if (
        _both_have_value(prediction, "username")
        and not features.username_exact
        and features.username_similarity < 0.80
    ):
        different.append("Username")

    if (
        _both_have_value(prediction, "display_name")
        and features.display_name_similarity < 0.80
    ):
        different.append("Display Name")

    if (
        _both_have_value(prediction, "first_name")
        and features.first_name_similarity < 0.80
    ):
        different.append("First Name")

    if (
        _both_have_value(prediction, "last_name")
        and features.last_name_similarity < 0.80
    ):
        different.append("Last Name")

    if (
        _both_have_value(prediction, "department")
        and not features.department_exact
        and features.department_similarity < 0.80
    ):
        different.append("Department")

    if (
        _both_have_value(prediction, "manager")
        and not features.manager_exact
        and features.manager_similarity < 0.80
    ):
        different.append("Manager")

    if (
        _both_have_value(prediction, "phone")
        and not features.phone_exact
        and features.phone_similarity < 0.80
    ):
        different.append("Phone")

    if (
        _both_have_value(prediction, "job_title")
        and features.title_similarity < 0.80
    ):
        different.append("Job Title")

    if (
        _both_have_value(prediction, "location")
        and features.location_similarity < 0.80
    ):
        different.append("Location")

    if (
        _both_have_value(prediction, "status")
        and not features.status_exact
    ):
        different.append("Status")

    return different