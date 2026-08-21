from __future__ import annotations

from collections.abc import Callable
import re

from app.ai.duplicate_engine.attribute_profiler import (
    AttributeCategory,
    AttributeProfile,
)
from app.ai.duplicate_engine.embedding_features import (
    AccountEmbeddingProfile,
    EmbeddingFeatures,
    calculate_embedding_features,
    calculate_embedding_features_from_profiles,
)
from app.ai.duplicate_engine.normalizer import (
    build_attribute_view,
    normalize_text,
)
from app.ai.duplicate_engine.similarity import (
    exact_match,
    similarity_ratio,
    token_similarity,
    username_similarity,
)
from app.ai.duplicate_engine.types import ComparisonFeatures, NormalizedAccount


IMPORTANT_COMPARISON_FIELDS = (
    "username", "display_name", "first_name", "last_name", "email",
    "employee_id", "department", "manager", "job_title", "phone", "location",
)


def _has_value(value: object) -> bool:
    return bool(str(value or "").strip())


def _safe_similarity(value_1: object, value_2: object, function: Callable[[str, str], float]) -> float:
    if not _has_value(value_1) or not _has_value(value_2):
        return 0.0
    return float(function(str(value_1), str(value_2)))


def _safe_exact(value_1: object, value_2: object) -> bool:
    if not _has_value(value_1) or not _has_value(value_2):
        return False
    return bool(exact_match(str(value_1), str(value_2)))


def count_missing_fields(account: NormalizedAccount) -> int:
    return sum(
        1
        for field_name in IMPORTANT_COMPARISON_FIELDS
        if not _has_value(getattr(account, field_name))
    )


def _canonical(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _dynamic_evidence(
    account_1: NormalizedAccount,
    account_2: NormalizedAccount,
    profiles: list[AttributeProfile] | None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "identifier": 0,
        "contact": 0,
        "name": 0,
        "org": 0,
        "unknown": 0,
        "conflicts": 0,
        "matched": [],
        "conflicting": [],
    }
    if not profiles:
        return result

    view_1 = build_attribute_view(account_1.raw)
    view_2 = build_attribute_view(account_2.raw)
    canonical_1 = {_canonical(str(key)): value for key, value in view_1.items()}
    canonical_2 = {_canonical(str(key)): value for key, value in view_2.items()}
    seen_attributes: set[str] = set()

    for profile in profiles:
        leaf = profile.name.split(".")[-1]
        canonical_name = _canonical(leaf)
        if not canonical_name or canonical_name in seen_attributes:
            continue
        seen_attributes.add(canonical_name)

        value_1 = canonical_1.get(canonical_name)
        value_2 = canonical_2.get(canonical_name)
        normalized_1 = normalize_text(value_1)
        normalized_2 = normalize_text(value_2)
        if not normalized_1 or not normalized_2:
            continue

        if normalized_1 == normalized_2:
            matched = result["matched"]
            assert isinstance(matched, list)
            matched.append(profile.name)
            if profile.category == AttributeCategory.IDENTIFIER:
                result["identifier"] = int(result["identifier"]) + 1
            elif profile.category == AttributeCategory.CONTACT:
                result["contact"] = int(result["contact"]) + 1
            elif profile.category == AttributeCategory.NAME:
                result["name"] = int(result["name"]) + 1
            elif profile.category == AttributeCategory.ORGANIZATIONAL:
                result["org"] = int(result["org"]) + 1
            elif profile.category == AttributeCategory.UNKNOWN:
                result["unknown"] = int(result["unknown"]) + 1
        elif profile.category == AttributeCategory.IDENTIFIER and profile.usefulness >= 55:
            result["conflicts"] = int(result["conflicts"]) + 1
            conflicting = result["conflicting"]
            assert isinstance(conflicting, list)
            conflicting.append(profile.name)

    return result


def extract_features(
    account_1: NormalizedAccount,
    account_2: NormalizedAccount,
    *,
    include_embeddings: bool = True,
    embedding_profile_1: AccountEmbeddingProfile | None = None,
    embedding_profile_2: AccountEmbeddingProfile | None = None,
    attribute_profiles: list[AttributeProfile] | None = None,
) -> ComparisonFeatures:
    if not include_embeddings:
        embedding_features = EmbeddingFeatures(
            identity_similarity=0.0,
            name_similarity=0.0,
            organization_similarity=0.0,
        )
    elif embedding_profile_1 is not None and embedding_profile_2 is not None:
        embedding_features = calculate_embedding_features_from_profiles(
            embedding_profile_1, embedding_profile_2
        )
    else:
        embedding_features = calculate_embedding_features(account_1, account_2)

    dynamic = _dynamic_evidence(account_1, account_2, attribute_profiles)

    return ComparisonFeatures(
        username_similarity=_safe_similarity(account_1.username, account_2.username, username_similarity),
        display_name_similarity=_safe_similarity(account_1.display_name, account_2.display_name, token_similarity),
        first_name_similarity=_safe_similarity(account_1.first_name, account_2.first_name, similarity_ratio),
        last_name_similarity=_safe_similarity(account_1.last_name, account_2.last_name, similarity_ratio),
        email_similarity=_safe_similarity(account_1.email, account_2.email, similarity_ratio),
        email_local_similarity=_safe_similarity(account_1.email_local_part, account_2.email_local_part, username_similarity),
        manager_similarity=_safe_similarity(account_1.manager, account_2.manager, token_similarity),
        department_similarity=_safe_similarity(account_1.department, account_2.department, token_similarity),
        title_similarity=_safe_similarity(account_1.job_title, account_2.job_title, token_similarity),
        location_similarity=_safe_similarity(account_1.location, account_2.location, token_similarity),
        phone_similarity=_safe_similarity(account_1.phone, account_2.phone, similarity_ratio),
        identity_embedding_similarity=embedding_features.identity_similarity,
        name_embedding_similarity=embedding_features.name_similarity,
        organization_embedding_similarity=embedding_features.organization_similarity,
        employee_id_exact=_safe_exact(account_1.employee_id, account_2.employee_id),
        email_exact=_safe_exact(account_1.email, account_2.email),
        username_exact=_safe_exact(account_1.username, account_2.username),
        phone_exact=_safe_exact(account_1.phone, account_2.phone),
        department_exact=_safe_exact(account_1.department, account_2.department),
        manager_exact=_safe_exact(account_1.manager, account_2.manager),
        status_exact=_safe_exact(account_1.status, account_2.status),
        same_application=_safe_exact(account_1.application, account_2.application),
        account_1_missing_fields=count_missing_fields(account_1),
        account_2_missing_fields=count_missing_fields(account_2),
        dynamic_identifier_matches=int(dynamic["identifier"]),
        dynamic_contact_matches=int(dynamic["contact"]),
        dynamic_name_matches=int(dynamic["name"]),
        dynamic_org_matches=int(dynamic["org"]),
        dynamic_unknown_matches=int(dynamic["unknown"]),
        dynamic_identifier_conflicts=int(dynamic["conflicts"]),
        dynamic_matched_attributes=tuple(dynamic["matched"]),
        dynamic_conflicting_attributes=tuple(dynamic["conflicting"]),
    )
