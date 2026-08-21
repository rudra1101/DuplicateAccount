import csv
import io
from pathlib import Path
from typing import BinaryIO

from app.models.account import Account


APPLICATION_ALIASES = ("application", "source", "system", "app")
USERNAME_ALIASES = (
    "username",
    "samaccountname",
    "userprincipalname",
    "upn",
    "uid",
    "accountname",
    "login",
    "loginname",
    "name",
)
EMAIL_ALIASES = ("email", "mail", "emailaddress", "workemail", "primaryemail")
DISPLAY_NAME_ALIASES = ("displayname", "fullname", "commonname", "cn")
EMPLOYEE_ID_ALIASES = (
    "employeeid",
    "employeenumber",
    "workerid",
    "workernumber",
    "personid",
    "personnumber",
)
DEPARTMENT_ALIASES = ("department", "departmentname", "businessunit", "orgunit")
MANAGER_ALIASES = ("manager", "managername", "managerid")
STATUS_ALIASES = ("status", "accountstatus", "state", "enabled")
CREATED_ALIASES = ("created", "createdat", "createddate", "whencreated")
ID_ALIASES = ("id", "accountid", "nativeidentity", "objectid", "uuid")


def _normalize_header(value: str) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


def _row_value(row: dict[str, str | None], aliases: tuple[str, ...]) -> str | None:
    normalized = {_normalize_header(key): value for key, value in row.items() if key}
    for alias in aliases:
        value = normalized.get(_normalize_header(alias))
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _clean_optional_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _parse_csv_content(
    raw_content: bytes,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    default_application: str | None = None,
    allow_dynamic_schema: bool = False,
) -> list[Account]:
    try:
        text_content = raw_content.decode(encoding)
    except LookupError as exc:
        raise ValueError(f"Unsupported file encoding: {encoding}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"Unable to decode the file using {encoding}.") from exc

    if delimiter == "\\t":
        delimiter = "\t"

    reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
    if reader.fieldnames is None:
        raise ValueError("The file does not contain a valid header row.")

    normalized_headers = {
        _normalize_header(header)
        for header in reader.fieldnames
        if header and str(header).strip()
    }

    # Manual CSV uploads retain the historical contract. Integration-driven
    # ingestion can use arbitrary application schemas and derives the legacy
    # fields needed by the current detector from common source aliases.
    if not allow_dynamic_schema:
        missing: list[str] = []
        if _normalize_header("application") not in normalized_headers:
            missing.append("application")
        if _normalize_header("username") not in normalized_headers:
            missing.append("username")
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))

    accounts: list[Account] = []

    for row_number, row in enumerate(reader, start=2):
        raw_attributes = {
            str(key).strip(): ("" if value is None else str(value).strip())
            for key, value in row.items()
            if key and str(key).strip()
        }

        application = _row_value(row, APPLICATION_ALIASES) or _clean_optional_value(default_application)
        if not application:
            raise ValueError(
                f"Unable to determine the application for row {row_number}. "
                "Configure exactly one application for this integration or provide an application attribute."
            )

        account_id = _row_value(row, ID_ALIASES)
        username = _row_value(row, USERNAME_ALIASES)
        email = _row_value(row, EMAIL_ALIASES) or ""

        if not username and allow_dynamic_schema:
            # Source schemas do not have to contain a literal username field.
            # Prefer a stable account id, then email, only as the legacy
            # identity key required by the current duplicate engine.
            username = account_id or email

        if not username:
            raise ValueError(
                f"Unable to determine an account identifier for row {row_number}. "
                "Expected a username/account-name style attribute, account id, or email."
            )

        accounts.append(
            Account(
                id=account_id,
                application=application,
                username=username,
                displayName=_row_value(row, DISPLAY_NAME_ALIASES) or "",
                email=email,
                employeeId=_row_value(row, EMPLOYEE_ID_ALIASES),
                department=_row_value(row, DEPARTMENT_ALIASES),
                manager=_row_value(row, MANAGER_ALIASES),
                status=_row_value(row, STATUS_ALIASES),
                created=_row_value(row, CREATED_ALIASES),
                rawAttributes=raw_attributes,
            )
        )

    if not accounts:
        raise ValueError("The file does not contain any account records.")

    return accounts


def load_uploaded_accounts(
    file: BinaryIO,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    default_application: str | None = None,
    allow_dynamic_schema: bool = False,
) -> list[Account]:
    raw_content = file.read()
    if not raw_content:
        raise ValueError("The account file is empty.")

    return _parse_csv_content(
        raw_content,
        delimiter=delimiter,
        encoding=encoding,
        default_application=default_application,
        allow_dynamic_schema=allow_dynamic_schema,
    )


def load_accounts(file_path: str | Path) -> list[Account]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Account CSV file was not found: {path}")
    if not path.is_file():
        raise ValueError(f"The provided account path is not a file: {path}")

    raw_content = path.read_bytes()
    if not raw_content:
        raise ValueError(f"The account CSV file is empty: {path}")

    return _parse_csv_content(raw_content)
