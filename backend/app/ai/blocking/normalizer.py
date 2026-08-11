from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any


NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")
WHITESPACE = re.compile(r"\s+")

ALIASES: dict[str, tuple[str, ...]] = {
    "id": (
        "id",
        "sourceAccountId",
        "source_account_id",
        "accountId",
        "account_id",
    ),
    "application": (
        "application",
        "source",
        "system",
    ),
    "username": (
        "username",
        "userName",
        "user_name",
        "login",
    ),
    "display_name": (
        "displayName",
        "display_name",
        "fullName",
        "full_name",
        "name",
    ),
    "first_name": (
        "firstName",
        "first_name",
        "givenName",
        "given_name",
    ),
    "last_name": (
        "lastName",
        "last_name",
        "surname",
        "familyName",
        "family_name",
    ),
    "email": (
        "email",
        "workEmail",
        "work_email",
        "mail",
    ),
    "employee_id": (
        "employeeId",
        "employee_id",
        "workerId",
        "worker_id",
        "workerID",
    ),
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = unicodedata.normalize(
        "NFKD",
        str(value),
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    return WHITESPACE.sub(
        " ",
        text.lower().strip(),
    )


def normalize_identifier(value: Any) -> str:
    text = normalize_text(value)

    return (
        NON_ALPHANUMERIC.sub("", text)
        if text
        else ""
    )


def normalize_email(value: Any) -> str:
    return normalize_text(value).replace(" ", "")


def normalize_email_local_part(value: Any) -> str:
    email = normalize_email(value)

    if not email:
        return ""

    return normalize_identifier(
        email.split("@", 1)[0]
    )


def get_account_value(
    account: Any,
    field_name: str,
) -> Any:
    aliases = ALIASES.get(
        field_name,
        (field_name,),
    )

    if isinstance(account, Mapping):
        for alias in aliases:
            if alias in account:
                return account.get(alias)

        return None

    for alias in aliases:
        if hasattr(account, alias):
            return getattr(account, alias)

    if hasattr(account, "model_dump"):
        payload = account.model_dump()

        for alias in aliases:
            if alias in payload:
                return payload.get(alias)

    return None


def get_source_key(
    account: Any,
    fallback_index: int,
) -> str:
    application = normalize_text(
        get_account_value(
            account,
            "application",
        )
    )

    source_id = normalize_identifier(
        get_account_value(
            account,
            "id",
        )
    )

    if source_id:
        return f"{application}:{source_id}"

    username = normalize_identifier(
        get_account_value(
            account,
            "username",
        )
    )

    if username:
        return (
            f"{application}:username:{username}"
        )

    return (
        f"{application}:index:{fallback_index}"
    )
