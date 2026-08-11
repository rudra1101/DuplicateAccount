from __future__ import annotations

from dataclasses import dataclass

from app.ai.duplicate_engine.types import (
    NormalizedAccount,
)
from app.ai.embeddings import (
    EmbeddingService,
    cosine_similarity,
    embedding_service,
)


@dataclass(frozen=True)
class AccountEmbeddingProfile:
    identity_vector: list[float]
    name_vector: list[float]
    organization_vector: list[float]


@dataclass(frozen=True)
class EmbeddingFeatures:
    identity_similarity: float
    name_similarity: float
    organization_similarity: float


def get_embedding_profile_key(
    account: NormalizedAccount,
) -> str:
    """
    Produce a stable key for an account's precomputed
    embedding profile.

    Application is included because source account IDs
    or usernames may overlap between applications.
    """

    identity = (
        account.original_id()
        or account.account_id
        or account.username
        or account.email
    )

    return (
        f"{account.application}:"
        f"{identity}"
    )


def join_non_empty(
    values: list[str],
) -> str:
    return " | ".join(
        value.strip()
        for value in values
        if value and value.strip()
    )


def build_identity_embedding_text(
    account: NormalizedAccount,
) -> str:
    return join_non_empty(
        [
            (
                f"display name: {account.display_name}"
                if account.display_name
                else ""
            ),
            (
                f"first name: {account.first_name}"
                if account.first_name
                else ""
            ),
            (
                f"last name: {account.last_name}"
                if account.last_name
                else ""
            ),
            (
                f"username: {account.username}"
                if account.username
                else ""
            ),
            (
                "email local part: "
                f"{account.email_local_part}"
                if account.email_local_part
                else ""
            ),
            (
                f"department: {account.department}"
                if account.department
                else ""
            ),
            (
                f"job title: {account.job_title}"
                if account.job_title
                else ""
            ),
            (
                f"manager: {account.manager}"
                if account.manager
                else ""
            ),
            (
                f"location: {account.location}"
                if account.location
                else ""
            ),
        ]
    )


def build_name_embedding_text(
    account: NormalizedAccount,
) -> str:
    return join_non_empty(
        [
            account.display_name,
            account.first_name,
            account.last_name,
            account.username,
            account.email_local_part,
        ]
    )


def build_organization_embedding_text(
    account: NormalizedAccount,
) -> str:
    return join_non_empty(
        [
            account.department,
            account.job_title,
            account.manager,
            account.location,
        ]
    )


def safe_cosine_similarity(
    vector_1: list[float],
    vector_2: list[float],
) -> float:
    if not vector_1 or not vector_2:
        return 0.0

    return max(
        0.0,
        cosine_similarity(
            vector_1,
            vector_2,
        ),
    )


def precompute_embedding_profiles(
    accounts: list[NormalizedAccount],
    *,
    service: EmbeddingService = embedding_service,
) -> dict[str, AccountEmbeddingProfile]:
    """
    Generate the three embedding vectors for every
    account in one batch request.

    Three vectors are created per account:

    1. Complete identity profile
    2. Name-related profile
    3. Organization-related profile
    """

    if not accounts:
        return {}

    texts: list[str] = []

    for account in accounts:
        texts.extend(
            [
                build_identity_embedding_text(
                    account
                ),
                build_name_embedding_text(
                    account
                ),
                build_organization_embedding_text(
                    account
                ),
            ]
        )

    vectors = service.embed_many(texts)

    expected_vector_count = (
        len(accounts) * 3
    )

    if len(vectors) != expected_vector_count:
        raise RuntimeError(
            "Unexpected number of embedding vectors. "
            f"Expected {expected_vector_count}, "
            f"received {len(vectors)}."
        )

    profiles: dict[
        str,
        AccountEmbeddingProfile,
    ] = {}

    vector_index = 0

    for account in accounts:
        profiles[
            get_embedding_profile_key(account)
        ] = AccountEmbeddingProfile(
            identity_vector=vectors[
                vector_index
            ],
            name_vector=vectors[
                vector_index + 1
            ],
            organization_vector=vectors[
                vector_index + 2
            ],
        )

        vector_index += 3

    return profiles


def calculate_embedding_features_from_profiles(
    profile_1: AccountEmbeddingProfile,
    profile_2: AccountEmbeddingProfile,
) -> EmbeddingFeatures:
    return EmbeddingFeatures(
        identity_similarity=(
            safe_cosine_similarity(
                profile_1.identity_vector,
                profile_2.identity_vector,
            )
        ),
        name_similarity=(
            safe_cosine_similarity(
                profile_1.name_vector,
                profile_2.name_vector,
            )
        ),
        organization_similarity=(
            safe_cosine_similarity(
                profile_1.organization_vector,
                profile_2.organization_vector,
            )
        ),
    )


def calculate_embedding_features(
    account_1: NormalizedAccount,
    account_2: NormalizedAccount,
    *,
    service: EmbeddingService = embedding_service,
) -> EmbeddingFeatures:
    """
    On-demand comparison used when precomputed profiles
    are not available, such as a direct two-account test.
    """

    profiles = precompute_embedding_profiles(
        [
            account_1,
            account_2,
        ],
        service=service,
    )

    profile_1 = profiles[
        get_embedding_profile_key(account_1)
    ]

    profile_2 = profiles[
        get_embedding_profile_key(account_2)
    ]

    return calculate_embedding_features_from_profiles(
        profile_1,
        profile_2,
    )