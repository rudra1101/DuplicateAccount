from app.ai.duplicate_engine.types import (
    ComparisonFeatures,
    MatchReason,
)


def percentage(
    value: float,
) -> float:
    return round(
        value * 100,
        1,
    )


def build_explanation(
    features: ComparisonFeatures,
) -> tuple[
    list[MatchReason],
    list[MatchReason],
]:
    reasons: list[
        MatchReason
    ] = []

    warnings: list[
        MatchReason
    ] = []

    if features.employee_id_exact:
        reasons.append(
            MatchReason(
                field="employeeId",
                message=(
                    "Employee IDs are identical."
                ),
                impact="VERY_HIGH",
                similarity=100.0,
            )
        )

    if features.email_exact:
        reasons.append(
            MatchReason(
                field="email",
                message=(
                    "Email addresses are identical."
                ),
                impact="VERY_HIGH",
                similarity=100.0,
            )
        )

    elif (
        features.email_similarity
        >= 0.85
    ):
        reasons.append(
            MatchReason(
                field="email",
                message=(
                    "Email addresses are "
                    "strongly similar."
                ),
                impact="HIGH",
                similarity=percentage(
                    features
                    .email_similarity
                ),
            )
        )

    if features.username_exact:
        reasons.append(
            MatchReason(
                field="username",
                message=(
                    "Usernames are identical."
                ),
                impact="HIGH",
                similarity=100.0,
            )
        )

    elif (
        features.username_similarity
        >= 0.80
    ):
        reasons.append(
            MatchReason(
                field="username",
                message=(
                    "Usernames are strongly similar."
                ),
                impact="MEDIUM",
                similarity=percentage(
                    features
                    .username_similarity
                ),
            )
        )

    if (
        features
        .display_name_similarity
        >= 0.85
    ):
        reasons.append(
            MatchReason(
                field="displayName",
                message=(
                    "Display names are strongly similar."
                ),
                impact="HIGH",
                similarity=percentage(
                    features
                    .display_name_similarity
                ),
            )
        )

    if features.phone_exact:
        reasons.append(
            MatchReason(
                field="phone",
                message=(
                    "Phone numbers are identical."
                ),
                impact="HIGH",
                similarity=100.0,
            )
        )

    if features.department_exact:
        reasons.append(
            MatchReason(
                field="department",
                message=(
                    "Both accounts belong to "
                    "the same department."
                ),
                impact="LOW",
                similarity=100.0,
            )
        )

    if features.manager_exact:
        reasons.append(
            MatchReason(
                field="manager",
                message=(
                    "Both accounts have "
                    "the same manager."
                ),
                impact="MEDIUM",
                similarity=100.0,
            )
        )

    if (
        features
        .name_embedding_similarity
        >= 0.85
    ):
        reasons.append(
            MatchReason(
                field="semanticName",
                message=(
                    "The account names are "
                    "semantically similar."
                ),
                impact="MEDIUM",
                similarity=percentage(
                    features
                    .name_embedding_similarity
                ),
            )
        )

    if (
        features
        .identity_embedding_similarity
        >= 0.88
    ):
        reasons.append(
            MatchReason(
                field="semanticIdentity",
                message=(
                    "The combined identity "
                    "profiles are semantically similar."
                ),
                impact="MEDIUM",
                similarity=percentage(
                    features
                    .identity_embedding_similarity
                ),
            )
        )

    if (
        features
        .organization_embedding_similarity
        >= 0.88
    ):
        reasons.append(
            MatchReason(
                field=(
                    "semanticOrganization"
                ),
                message=(
                    "The organizational context "
                    "is semantically similar."
                ),
                impact="LOW",
                similarity=percentage(
                    features
                    .organization_embedding_similarity
                ),
            )
        )

    if (
        features.email_similarity > 0
        and features.email_similarity
        < 0.35
    ):
        warnings.append(
            MatchReason(
                field="email",
                message=(
                    "Email addresses are "
                    "substantially different."
                ),
                impact="HIGH",
                similarity=percentage(
                    features
                    .email_similarity
                ),
            )
        )

    if (
        features
        .display_name_similarity
        > 0
        and features
        .display_name_similarity
        < 0.45
    ):
        warnings.append(
            MatchReason(
                field="displayName",
                message=(
                    "Display names have "
                    "low textual similarity."
                ),
                impact="MEDIUM",
                similarity=percentage(
                    features
                    .display_name_similarity
                ),
            )
        )

    if (
        features
        .display_name_similarity
        < 0.55
        and features
        .name_embedding_similarity
        >= 0.82
    ):
        warnings.append(
            MatchReason(
                field="semanticName",
                message=(
                    "Name text differs, but semantic "
                    "similarity indicates a possible "
                    "alias or alternate name."
                ),
                impact="MEDIUM",
                similarity=percentage(
                    features
                    .name_embedding_similarity
                ),
            )
        )

    total_missing = (
        features
        .account_1_missing_fields
        + features
        .account_2_missing_fields
    )

    if total_missing >= 8:
        warnings.append(
            MatchReason(
                field="dataQuality",
                message=(
                    "Several comparison fields "
                    "are missing, reducing confidence."
                ),
                impact="MEDIUM",
            )
        )

    return reasons, warnings