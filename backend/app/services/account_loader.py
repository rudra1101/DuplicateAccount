import csv
import io
from pathlib import Path
from typing import BinaryIO

from app.models.account import Account


def load_uploaded_accounts(file: BinaryIO) -> list[Account]:
    """
    Load accounts from a FastAPI uploaded CSV file.
    """

    raw_content = file.read()

    if not raw_content:
        raise ValueError("The uploaded CSV file is empty.")

    return _parse_csv_content(raw_content)


def load_accounts(file_path: str | Path) -> list[Account]:
    """
    Load accounts from a CSV file stored on disk.

    This function is retained because detect.py currently imports it.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Account CSV file was not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"The provided account path is not a file: {path}"
        )

    raw_content = path.read_bytes()

    if not raw_content:
        raise ValueError(
            f"The account CSV file is empty: {path}"
        )

    return _parse_csv_content(raw_content)


def _parse_csv_content(
    raw_content: bytes,
) -> list[Account]:
    """
    Parse CSV bytes and return validated Account objects.
    """

    try:
        text_content = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "Unable to read the CSV file. "
            "Please use UTF-8 encoding."
        ) from exc

    reader = csv.DictReader(
        io.StringIO(text_content)
    )

    if reader.fieldnames is None:
        raise ValueError(
            "The CSV file does not contain a valid header row."
        )

    normalized_headers = {
        header.strip()
        for header in reader.fieldnames
        if header
    }

    required_headers = {
        "application",
        "username",
    }

    missing_headers = (
        required_headers
        - normalized_headers
    )

    if missing_headers:
        raise ValueError(
            "Missing required CSV columns: "
            + ", ".join(
                sorted(missing_headers)
            )
        )

    accounts: list[Account] = []

    for row_number, row in enumerate(
        reader,
        start=2,
    ):
        application = _clean_value(
            row.get("application")
        )

        username = _clean_value(
            row.get("username")
        )

        if not application:
            raise ValueError(
                f"Missing application at CSV row {row_number}."
            )

        if not username:
            raise ValueError(
                f"Missing username at CSV row {row_number}."
            )

        account = Account(
            id=_clean_optional_value(
                row.get("id")
            ),
            application=application,
            username=username,
            displayName=_clean_value(
                row.get("displayName")
            ),
            email=_clean_value(
                row.get("email")
            ),
            employeeId=_clean_optional_value(
                row.get("employeeId")
            ),
            department=_clean_optional_value(
                row.get("department")
            ),
            manager=_clean_optional_value(
                row.get("manager")
            ),
            status=_clean_optional_value(
                row.get("status")
            ),
            created=_clean_optional_value(
                row.get("created")
            ),
        )

        accounts.append(account)

    if not accounts:
        raise ValueError(
            "The CSV file does not contain any account records."
        )

    return accounts


def _clean_value(
    value: str | None,
) -> str:
    if value is None:
        return ""

    return value.strip()


def _clean_optional_value(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    cleaned_value = value.strip()

    return cleaned_value or None

def load_uploaded_accounts(
    file,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
) -> list[Account]:
    """
    Load account records from an uploaded or connector-provided
    delimited file.
    """

    raw_content = file.read()

    if not raw_content:
        raise ValueError(
            "The account file is empty."
        )

    try:
        text_content = raw_content.decode(
            encoding
        )
    except LookupError as exc:
        raise ValueError(
            f"Unsupported file encoding: {encoding}"
        ) from exc
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Unable to decode the file using {encoding}."
        ) from exc

    if delimiter == "\\t":
        delimiter = "\t"

    reader = csv.DictReader(
        io.StringIO(text_content),
        delimiter=delimiter,
    )

    if reader.fieldnames is None:
        raise ValueError(
            "The file does not contain a valid header row."
        )

    normalized_headers = {
        header.strip()
        for header in reader.fieldnames
        if header
    }

    required_headers = {
        "application",
        "username",
    }

    missing_headers = (
        required_headers - normalized_headers
    )

    if missing_headers:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(
                sorted(missing_headers)
            )
        )

    accounts: list[Account] = []

    for row_number, row in enumerate(
        reader,
        start=2,
    ):
        application = _clean_value(
            row.get("application")
        )

        username = _clean_value(
            row.get("username")
        )

        if not application:
            raise ValueError(
                f"Missing application at row {row_number}."
            )

        if not username:
            raise ValueError(
                f"Missing username at row {row_number}."
            )

        accounts.append(
            Account(
                id=_clean_optional_value(
                    row.get("id")
                ),
                application=application,
                username=username,
                displayName=_clean_value(
                    row.get("displayName")
                ),
                email=_clean_value(
                    row.get("email")
                ),
                employeeId=_clean_optional_value(
                    row.get("employeeId")
                ),
                department=_clean_optional_value(
                    row.get("department")
                ),
                manager=_clean_optional_value(
                    row.get("manager")
                ),
                status=_clean_optional_value(
                    row.get("status")
                ),
                created=_clean_optional_value(
                    row.get("created")
                ),
            )
        )

    if not accounts:
        raise ValueError(
            "The file does not contain any account records."
        )

    return accounts