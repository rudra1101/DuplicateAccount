import re
import unicodedata
from typing import Any

from app.ai.duplicate_engine.types import (
    NormalizedAccount,
)


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "account_id": (
        "account_id",
        "accountId",
        "id",
        "native_identity",
        "nativeIdentity",
    ),
    "application": (
        "application",
        "application_name",
        "applicationName",
        "source",
        "source_name",
    ),
    "username": (
        "username",
        "user_name",
        "userName",
        "account_name",
        "accountName",
        "sam_account_name",
        "sAMAccountName",
        "samAccountName",
    ),
    "display_name": (
        "display_name",
        "displayName",
        "name",
        "full_name",
        "fullName",
    ),
    "first_name": (
        "first_name",
        "firstName",
        "firstname",
        "given_name",
        "givenName",
    ),
    "last_name": (
        "last_name",
        "lastName",
        "lastname",
        "surname",
        "sn",
    ),
    "email": (
        "email",
        "mail",
        "email_address",
        "emailAddress",
        "userPrincipalName",
        "upn",
    ),
    "employee_id": (
        "employee_id",
        "employeeId",
        "employeeID",
        "worker_id",
        "workerId",
        "person_number",
    ),
    "department": (
        "department",
        "department_name",
        "departmentName",
    ),
    "manager": (
        "manager",
        "manager_name",
        "managerName",
        "manager_id",
        "managerId",
    ),
    "job_title": (
        "job_title",
        "jobTitle",
        "title",
        "designation",
    ),
    "phone": (
        "phone",
        "telephone",
        "telephoneNumber",
        "mobile",
        "mobilePhone",
    ),
    "location": (
        "location",
        "office",
        "office_location",
        "officeLocation",
        "city",
    ),
    "status": (
        "status",
        "account_status",
        "accountStatus",
        "enabled",
        "active",
    ),
    "created_at": (
        "created_at",
        "createdAt",
        "created",
        "creation_date",
        "creationDate",
    ),
}


def get_first_value(
    account: dict[str, Any],
    aliases: tuple[str, ...],
) -> Any:
    for alias in aliases:
        value = account.get(alias)

        if value is not None:
            return value

    return None


def normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    normalized = unicodedata.normalize(
        "NFKD",
        str(value),
    )

    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )

    normalized = normalized.strip().lower()

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized


def normalize_identifier(
    value: Any,
) -> str:
    normalized = normalize_text(value)

    return re.sub(
        r"[^a-z0-9@._+-]",
        "",
        normalized,
    )


def normalize_name(
    value: Any,
) -> str:
    normalized = normalize_text(value)

    normalized = re.sub(
        r"[^a-z0-9\s'-]",
        " ",
        normalized,
    )

    return re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()


def normalize_phone(
    value: Any,
) -> str:
    if value is None:
        return ""

    digits = re.sub(
        r"\D",
        "",
        str(value),
    )

    # Compare the last 10 digits to tolerate
    # country-code and formatting differences.
    if len(digits) > 10:
        return digits[-10:]

    return digits


def normalize_status(
    value: Any,
) -> str:
    if isinstance(value, bool):
        return (
            "active"
            if value
            else "inactive"
        )

    normalized = normalize_text(value)

    active_values = {
        "active",
        "enabled",
        "true",
        "1",
        "yes",
    }

    inactive_values = {
        "inactive",
        "disabled",
        "false",
        "0",
        "no",
        "terminated",
    }

    if normalized in active_values:
        return "active"

    if normalized in inactive_values:
        return "inactive"

    return normalized


def split_email(
    email: str,
) -> tuple[str, str]:
    if "@" not in email:
        return email, ""

    local_part, domain = email.split(
        "@",
        maxsplit=1,
    )

    return local_part, domain


def derive_names(
    *,
    display_name: str,
    first_name: str,
    last_name: str,
) -> tuple[str, str]:
    if first_name or last_name:
        return first_name, last_name

    parts = display_name.split()

    if not parts:
        return "", ""

    if len(parts) == 1:
        return parts[0], ""

    return parts[0], parts[-1]


def normalize_account(
    account: dict[str, Any],
) -> NormalizedAccount:
    account_id = normalize_identifier(
        get_first_value(
            account,
            FIELD_ALIASES["account_id"],
        )
    )

    application = normalize_text(
        get_first_value(
            account,
            FIELD_ALIASES["application"],
        )
    )

    username = normalize_identifier(
        get_first_value(
            account,
            FIELD_ALIASES["username"],
        )
    )

    display_name = normalize_name(
        get_first_value(
            account,
            FIELD_ALIASES["display_name"],
        )
    )

    first_name = normalize_name(
        get_first_value(
            account,
            FIELD_ALIASES["first_name"],
        )
    )

    last_name = normalize_name(
        get_first_value(
            account,
            FIELD_ALIASES["last_name"],
        )
    )

    first_name, last_name = derive_names(
        display_name=display_name,
        first_name=first_name,
        last_name=last_name,
    )

    email = normalize_identifier(
        get_first_value(
            account,
            FIELD_ALIASES["email"],
        )
    )

    email_local_part, email_domain = (
        split_email(email)
    )

    employee_id = normalize_identifier(
        get_first_value(
            account,
            FIELD_ALIASES["employee_id"],
        )
    )

    department = normalize_text(
        get_first_value(
            account,
            FIELD_ALIASES["department"],
        )
    )

    manager = normalize_name(
        get_first_value(
            account,
            FIELD_ALIASES["manager"],
        )
    )

    job_title = normalize_text(
        get_first_value(
            account,
            FIELD_ALIASES["job_title"],
        )
    )

    phone = normalize_phone(
        get_first_value(
            account,
            FIELD_ALIASES["phone"],
        )
    )

    location = normalize_text(
        get_first_value(
            account,
            FIELD_ALIASES["location"],
        )
    )

    status = normalize_status(
        get_first_value(
            account,
            FIELD_ALIASES["status"],
        )
    )

    created_value = get_first_value(
        account,
        FIELD_ALIASES["created_at"],
    )

    return NormalizedAccount(
        account_id=account_id,
        application=application,
        username=username,
        display_name=display_name,
        first_name=first_name,
        last_name=last_name,
        email=email,
        email_local_part=email_local_part,
        email_domain=email_domain,
        employee_id=employee_id,
        department=department,
        manager=manager,
        job_title=job_title,
        phone=phone,
        location=location,
        status=status,
        created_at=(
            str(created_value)
            if created_value is not None
            else None
        ),
        raw=dict(account),
    )