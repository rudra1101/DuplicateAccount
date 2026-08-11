from __future__ import annotations

from typing import Any


FEATURE_NAMES = [
    "username_similarity",
    "display_name_similarity",
    "first_name_similarity",
    "last_name_similarity",
    "email_similarity",
    "email_local_similarity",
    "manager_similarity",
    "department_similarity",
    "title_similarity",
    "location_similarity",
    "phone_similarity",
    "identity_embedding_similarity",
    "name_embedding_similarity",
    "organization_embedding_similarity",
    "employee_id_exact",
    "email_exact",
    "username_exact",
    "phone_exact",
    "department_exact",
    "manager_exact",
    "status_exact",
    "same_application",
    "account_1_missing_fields",
    "account_2_missing_fields",
]


def _to_float(
    value: Any,
) -> float:
    if value is None:
        return 0.0

    if isinstance(value, bool):
        return 1.0 if value else 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def features_to_vector(
    features: dict[str, Any],
) -> list[float]:
    return [
        _to_float(
            features.get(feature_name)
        )
        for feature_name in FEATURE_NAMES
    ]