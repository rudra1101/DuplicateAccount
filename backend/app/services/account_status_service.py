from __future__ import annotations

from typing import Any, TypeVar


ACCOUNT_STATE_ACTIVE = "ACTIVE"
ACCOUNT_STATE_INACTIVE = "INACTIVE"
ACCOUNT_STATE_UNKNOWN = "UNKNOWN"
ACCOUNT_STATES = {
    ACCOUNT_STATE_ACTIVE,
    ACCOUNT_STATE_INACTIVE,
    ACCOUNT_STATE_UNKNOWN,
}

DEFAULT_ACTIVE_VALUES = {
    "1",
    "active",
    "enabled",
    "enable",
    "true",
    "yes",
}
DEFAULT_INACTIVE_VALUES = {
    "0",
    "disabled",
    "disable",
    "false",
    "inactive",
    "locked",
    "suspended",
    "terminated",
    "no",
}

AccountLike = TypeVar("AccountLike")


def _normalized_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value or "").strip().casefold()


def normalize_status_values(values: list[str] | tuple[str, ...] | set[str] | None) -> set[str]:
    return {
        normalized
        for value in (values or [])
        if (normalized := _normalized_value(value))
    }


def canonical_account_state(
    value: Any,
    *,
    active_values: list[str] | tuple[str, ...] | set[str] | None = None,
    inactive_values: list[str] | tuple[str, ...] | set[str] | None = None,
) -> str:
    normalized = _normalized_value(value)
    if not normalized:
        return ACCOUNT_STATE_UNKNOWN

    configured_active = normalize_status_values(active_values)
    configured_inactive = normalize_status_values(inactive_values)

    active = configured_active or DEFAULT_ACTIVE_VALUES
    inactive = configured_inactive or DEFAULT_INACTIVE_VALUES

    if normalized in inactive:
        return ACCOUNT_STATE_INACTIVE
    if normalized in active:
        return ACCOUNT_STATE_ACTIVE
    return ACCOUNT_STATE_UNKNOWN


def account_is_duplicate_eligible(status: Any) -> bool:
    """Inactive accounts stay in inventory but are excluded from duplicate detection.

    UNKNOWN deliberately remains eligible so existing integrations without a configured
    status mapping keep their current duplicate-detection behavior.
    """

    return str(status or ACCOUNT_STATE_UNKNOWN).strip().upper() != ACCOUNT_STATE_INACTIVE


def duplicate_eligible_accounts(accounts: list[AccountLike]) -> list[AccountLike]:
    return [
        account
        for account in accounts
        if account_is_duplicate_eligible(getattr(account, "status", None))
    ]
