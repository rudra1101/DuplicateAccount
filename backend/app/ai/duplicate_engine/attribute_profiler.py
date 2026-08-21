from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

from app.ai.duplicate_engine.normalizer import (
    build_attribute_view,
    normalize_text,
)
from app.ai.duplicate_engine.types import NormalizedAccount


class AttributeCategory(str, Enum):
    SOURCE_KEY = "SOURCE_KEY"
    IDENTIFIER = "IDENTIFIER"
    CONTACT = "CONTACT"
    NAME = "NAME"
    ORGANIZATIONAL = "ORGANIZATIONAL"
    STATUS = "STATUS"
    DATE = "DATE"
    TECHNICAL = "TECHNICAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AttributeProfile:
    name: str
    category: AttributeCategory
    coverage: float
    uniqueness: float
    cardinality: int
    non_empty_count: int
    usefulness: float
    blocking_eligible: bool


def _canonical_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _clean_value(value: Any) -> str:
    if value is None or not _is_scalar(value):
        return ""
    return normalize_text(value)


def classify_attribute(name: str) -> AttributeCategory:
    key = _canonical_name(name.split(".")[-1])

    source_keys = {
        "id", "accountid", "nativeidentity", "objectid", "uuid", "guid",
        "sourceaccountid", "identityid", "recordid",
    }
    identifier_tokens = (
        "employeeid", "employeenumber", "workernumber", "workerid",
        "personnumber", "personid", "staffid", "login", "username",
        "samaccountname", "accountname", "uid", "upn",
    )
    contact_tokens = (
        "email", "mail", "phone", "mobile", "telephone",
    )
    name_tokens = (
        "displayname", "fullname", "firstname", "lastname", "givenname",
        "surname", "commonname", "preferredname", "name",
    )
    org_tokens = (
        "department", "manager", "title", "designation", "location",
        "office", "businessunit", "orgunit", "costcenter", "company",
    )
    status_tokens = (
        "status", "state", "enabled", "active", "lifecycle",
    )
    date_tokens = (
        "created", "updated", "modified", "timestamp", "date", "time",
        "lastlogin", "lastlogon", "whencreated", "whenchanged",
    )
    technical_tokens = (
        "dn", "distinguishedname", "objectclass", "etag", "hash", "checksum",
        "version", "schema", "metadata", "tenant", "sourceid",
    )

    if key in source_keys or key.endswith("guid") or key.endswith("uuid"):
        return AttributeCategory.SOURCE_KEY
    if any(token in key for token in contact_tokens):
        return AttributeCategory.CONTACT
    if any(token in key for token in identifier_tokens):
        return AttributeCategory.IDENTIFIER
    if any(token == key or key.endswith(token) for token in name_tokens):
        return AttributeCategory.NAME
    if any(token in key for token in org_tokens):
        return AttributeCategory.ORGANIZATIONAL
    if any(token in key for token in status_tokens):
        return AttributeCategory.STATUS
    if any(token in key for token in date_tokens):
        return AttributeCategory.DATE
    if any(token in key for token in technical_tokens):
        return AttributeCategory.TECHNICAL
    return AttributeCategory.UNKNOWN


def _category_factor(category: AttributeCategory) -> float:
    return {
        AttributeCategory.IDENTIFIER: 1.00,
        AttributeCategory.CONTACT: 0.95,
        AttributeCategory.NAME: 0.82,
        AttributeCategory.ORGANIZATIONAL: 0.45,
        AttributeCategory.UNKNOWN: 0.30,
        AttributeCategory.STATUS: 0.08,
        AttributeCategory.DATE: 0.03,
        AttributeCategory.SOURCE_KEY: 0.0,
        AttributeCategory.TECHNICAL: 0.0,
    }[category]


def profile_application_attributes(
    accounts: list[NormalizedAccount],
) -> list[AttributeProfile]:
    if not accounts:
        return []

    values_by_attribute: dict[str, list[str]] = {}

    for account in accounts:
        view = build_attribute_view(account.raw)
        for name, value in view.items():
            cleaned = _clean_value(value)
            if not cleaned:
                continue
            values_by_attribute.setdefault(str(name), []).append(cleaned)

    total_accounts = len(accounts)
    profiles: list[AttributeProfile] = []

    for name, values in values_by_attribute.items():
        non_empty_count = len(values)
        if non_empty_count == 0:
            continue

        counts = Counter(values)
        cardinality = len(counts)
        coverage = non_empty_count / total_accounts
        uniqueness = cardinality / non_empty_count
        category = classify_attribute(name)

        # Useful duplicate indicators need good coverage and enough selectivity,
        # but should still be able to repeat for genuine duplicate accounts.
        selectivity = max(0.0, min(1.0, uniqueness))
        coverage_factor = max(0.0, min(1.0, coverage))
        usefulness = (
            100.0
            * coverage_factor
            * (0.35 + 0.65 * selectivity)
            * _category_factor(category)
        )

        repeated_values = sum(1 for count in counts.values() if count > 1)
        blocking_eligible = (
            category
            in {
                AttributeCategory.IDENTIFIER,
                AttributeCategory.CONTACT,
                AttributeCategory.NAME,
                AttributeCategory.ORGANIZATIONAL,
                AttributeCategory.UNKNOWN,
            }
            and coverage >= 0.20
            and cardinality >= 2
            and repeated_values > 0
            and usefulness >= 12.0
        )

        profiles.append(
            AttributeProfile(
                name=name,
                category=category,
                coverage=round(coverage, 4),
                uniqueness=round(uniqueness, 4),
                cardinality=cardinality,
                non_empty_count=non_empty_count,
                usefulness=round(usefulness, 2),
                blocking_eligible=blocking_eligible,
            )
        )

    profiles.sort(key=lambda item: (-item.usefulness, item.name.lower()))
    return profiles


def dynamic_blocking_profiles(
    accounts: list[NormalizedAccount],
    *,
    limit: int = 12,
) -> list[AttributeProfile]:
    return [
        profile
        for profile in profile_application_attributes(accounts)
        if profile.blocking_eligible
    ][:limit]
