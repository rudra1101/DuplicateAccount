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


# These are already handled by the legacy semantic feature extractor. Dynamic
# profiling must not count the same evidence a second time.
LEGACY_HANDLED_FIELDS = {
    "username", "userName", "user_name", "accountName", "account_name",
    "samAccountName", "sAMAccountName", "uid", "upn",
    "email", "mail", "emailAddress", "email_address", "userPrincipalName",
    "employeeId", "employeeID", "employee_id", "employeeNumber",
    "workerId", "worker_id", "personNumber", "person_number",
    "displayName", "display_name", "fullName", "full_name", "name",
    "firstName", "first_name", "givenName", "given_name",
    "lastName", "last_name", "surname", "sn",
    "department", "departmentName", "department_name",
    "manager", "managerName", "manager_name", "managerId", "manager_id",
    "jobTitle", "job_title", "title", "designation",
    "phone", "mobile", "telephone", "telephoneNumber", "mobilePhone",
    "location", "office", "officeLocation", "office_location", "city",
    "status", "accountStatus", "account_status", "enabled", "active",
}
LEGACY_HANDLED_CANONICAL = {_canonical_name(value) for value in LEGACY_HANDLED_FIELDS}

_BOOLEAN_VALUES = {
    "true", "false", "0", "1", "yes", "no", "y", "n", "enabled", "disabled",
}

_ISO_DATE_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[t\s].*)?$",
    re.IGNORECASE,
)

_EPOCH_PATTERN = re.compile(r"^\d{10,13}$")


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _clean_value(value: Any) -> str:
    if value is None or not _is_scalar(value):
        return ""
    return normalize_text(value)


def classify_attribute(name: str) -> AttributeCategory:
    """Classify from field semantics before looking at value shape.

    Ordering matters: lifecycleState.stateName should be STATUS, not NAME,
    and lastRefresh should be DATE rather than UNKNOWN.
    """
    key = _canonical_name(name.split(".")[-1])
    full_key = _canonical_name(name)

    source_keys = {
        "id", "accountid", "nativeidentity", "objectid", "uuid", "guid",
        "sourceaccountid", "identityid", "recordid",
    }
    identifier_tokens = (
        "employeeid", "employeenumber", "workernumber", "workerid",
        "personnumber", "personid", "staffid", "payrollnumber", "payrollid",
        "badgeid", "personnelnumber", "login", "username", "samaccountname",
        "accountname", "uid", "upn",
    )
    contact_tokens = ("email", "mail", "phone", "mobile", "telephone")
    status_tokens = (
        "status", "state", "enabled", "active", "inactive", "lifecycle",
        "disabled", "locked", "managerflag", "ismanager",
    )
    date_tokens = (
        "created", "updated", "modified", "timestamp", "date", "time",
        "lastlogin", "lastlogon", "whencreated", "whenchanged", "refresh",
        "synced", "sync", "lastseen", "lastaccess", "lastupdate",
    )
    technical_tokens = (
        "dn", "distinguishedname", "objectclass", "etag", "hash", "checksum",
        "version", "schema", "metadata", "tenant", "sourceid", "requestid",
    )
    org_tokens = (
        "department", "manager", "title", "designation", "location",
        "office", "businessunit", "orgunit", "costcenter", "company",
    )
    name_tokens = (
        "displayname", "fullname", "firstname", "lastname", "givenname",
        "surname", "commonname", "preferredname", "name",
    )

    if key in source_keys or key.endswith("guid") or key.endswith("uuid"):
        return AttributeCategory.SOURCE_KEY
    if any(token in full_key for token in technical_tokens):
        return AttributeCategory.TECHNICAL
    if any(token in full_key for token in date_tokens):
        return AttributeCategory.DATE
    if any(token in full_key for token in status_tokens):
        return AttributeCategory.STATUS
    if any(token in key for token in contact_tokens):
        return AttributeCategory.CONTACT
    if any(token in key for token in identifier_tokens):
        return AttributeCategory.IDENTIFIER
    if any(token in key for token in org_tokens):
        return AttributeCategory.ORGANIZATIONAL
    if any(token == key or key.endswith(token) for token in name_tokens):
        return AttributeCategory.NAME
    return AttributeCategory.UNKNOWN


def _refine_category_from_values(
    category: AttributeCategory,
    values: list[str],
) -> AttributeCategory:
    """Reject common false-positive identity attributes using value shape."""
    if not values:
        return category

    sampled = values[:100]
    lowered = [value.strip().lower() for value in sampled if value.strip()]
    if not lowered:
        return category

    boolean_ratio = sum(value in _BOOLEAN_VALUES for value in lowered) / len(lowered)
    if boolean_ratio >= 0.95:
        return AttributeCategory.STATUS

    date_ratio = sum(
        bool(_ISO_DATE_PATTERN.match(value) or _EPOCH_PATTERN.match(value))
        for value in lowered
    ) / len(lowered)
    if date_ratio >= 0.90:
        return AttributeCategory.DATE

    return category


def _category_factor(category: AttributeCategory) -> float:
    return {
        AttributeCategory.IDENTIFIER: 1.00,
        AttributeCategory.CONTACT: 0.95,
        AttributeCategory.NAME: 0.82,
        AttributeCategory.ORGANIZATIONAL: 0.45,
        AttributeCategory.UNKNOWN: 0.22,
        AttributeCategory.STATUS: 0.05,
        AttributeCategory.DATE: 0.0,
        AttributeCategory.SOURCE_KEY: 0.0,
        AttributeCategory.TECHNICAL: 0.0,
    }[category]


def _bucket_is_reasonable(
    *,
    category: AttributeCategory,
    largest_bucket: int,
    non_empty_count: int,
) -> bool:
    """Prevent broad low-value buckets without suppressing real identifiers.

    A repeated identifier value is exactly what duplicate detection is looking
    for, so a tiny test/application sample such as 2 of 3 accounts sharing a
    payroll number must remain eligible. Broad UNKNOWN/organizational values
    are still restricted aggressively because they create noisy candidate sets.
    Candidate generation separately enforces max_block_size for absolute scale.
    """
    if non_empty_count <= 0:
        return False

    ratio = largest_bucket / non_empty_count

    if category == AttributeCategory.IDENTIFIER:
        return largest_bucket <= 100
    if category == AttributeCategory.CONTACT:
        return largest_bucket <= 50 and (non_empty_count < 10 or ratio <= 0.60)
    if category == AttributeCategory.NAME:
        return largest_bucket <= 50 and (non_empty_count < 10 or ratio <= 0.50)
    if category == AttributeCategory.ORGANIZATIONAL:
        return largest_bucket <= 50 and ratio <= 0.30
    if category == AttributeCategory.UNKNOWN:
        return largest_bucket <= 25 and ratio <= 0.20

    return False


def profile_application_attributes(accounts: list[NormalizedAccount]) -> list[AttributeProfile]:
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
        category = _refine_category_from_values(
            classify_attribute(name),
            values,
        )
        leaf_canonical = _canonical_name(name.split(".")[-1])

        selectivity = max(0.0, min(1.0, uniqueness))
        coverage_factor = max(0.0, min(1.0, coverage))
        usefulness = (
            100.0
            * coverage_factor
            * (0.35 + 0.65 * selectivity)
            * _category_factor(category)
        )

        repeated_values = sum(1 for count in counts.values() if count > 1)
        largest_bucket = max(counts.values()) if counts else 0
        already_handled = leaf_canonical in LEGACY_HANDLED_CANONICAL

        category_allowed = category in {
            AttributeCategory.IDENTIFIER,
            AttributeCategory.CONTACT,
            AttributeCategory.NAME,
            AttributeCategory.ORGANIZATIONAL,
            AttributeCategory.UNKNOWN,
        }
        minimum_cardinality = 2 if category in {
            AttributeCategory.IDENTIFIER,
            AttributeCategory.CONTACT,
            AttributeCategory.NAME,
        } else 4
        minimum_usefulness = 18.0 if category == AttributeCategory.UNKNOWN else 12.0

        blocking_eligible = (
            not already_handled
            and category_allowed
            and coverage >= 0.20
            and cardinality >= minimum_cardinality
            and repeated_values > 0
            and _bucket_is_reasonable(
                category=category,
                largest_bucket=largest_bucket,
                non_empty_count=non_empty_count,
            )
            and usefulness >= minimum_usefulness
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
