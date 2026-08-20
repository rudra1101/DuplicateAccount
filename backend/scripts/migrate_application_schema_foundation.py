from __future__ import annotations

from sqlalchemy import inspect, text

from app.database.base import Base
from app.database.session import engine
import app.db_models  # noqa: F401 - registers all models with metadata


ACCOUNT_COLUMNS = {
    "application_id": "INTEGER",
    "schema_id": "INTEGER",
    "raw_attributes": "JSON",
}


def add_missing_account_columns() -> list[str]:
    inspector = inspect(engine)

    if "accounts" not in inspector.get_table_names():
        return []

    existing = {
        column["name"]
        for column in inspector.get_columns("accounts")
    }

    added: list[str] = []

    with engine.begin() as connection:
        for column_name, sql_type in ACCOUNT_COLUMNS.items():
            if column_name in existing:
                continue

            connection.execute(
                text(
                    f"ALTER TABLE accounts "
                    f"ADD COLUMN {column_name} {sql_type}"
                )
            )
            added.append(column_name)

        # SQLite cannot add FK constraints with a simple ALTER TABLE,
        # but indexes keep the new lookup paths efficient. SQLAlchemy's
        # model-level FKs document the intended relationship for fresh DBs.
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_accounts_application_id "
                "ON accounts (application_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_accounts_schema_id "
                "ON accounts (schema_id)"
            )
        )

    return added


def backfill_applications() -> tuple[int, int]:
    """
    Convert existing per-account application names into first-class
    application records for scans that are already linked to integrations.

    Legacy scans without integration_id remain untouched.
    """

    with engine.begin() as connection:
        before = connection.execute(
            text("SELECT COUNT(*) FROM applications")
        ).scalar_one()

        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO applications (
                    integration_id,
                    name,
                    display_name,
                    object_type,
                    enabled,
                    created_at,
                    updated_at
                )
                SELECT DISTINCT
                    scans.integration_id,
                    accounts.application,
                    accounts.application,
                    'ACCOUNT',
                    1,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                FROM accounts
                JOIN scans ON scans.id = accounts.scan_id
                WHERE scans.integration_id IS NOT NULL
                  AND accounts.application IS NOT NULL
                  AND TRIM(accounts.application) <> ''
                """
            )
        )

        after = connection.execute(
            text("SELECT COUNT(*) FROM applications")
        ).scalar_one()

        connection.execute(
            text(
                """
                UPDATE accounts
                SET application_id = (
                    SELECT applications.id
                    FROM applications
                    JOIN scans
                      ON scans.integration_id = applications.integration_id
                    WHERE scans.id = accounts.scan_id
                      AND applications.name = accounts.application
                    LIMIT 1
                )
                WHERE application_id IS NULL
                  AND EXISTS (
                    SELECT 1
                    FROM scans
                    WHERE scans.id = accounts.scan_id
                      AND scans.integration_id IS NOT NULL
                  )
                """
            )
        )

        linked_accounts = connection.execute(
            text(
                "SELECT COUNT(*) FROM accounts "
                "WHERE application_id IS NOT NULL"
            )
        ).scalar_one()

    return int(after - before), int(linked_accounts)


def main() -> None:
    # Creates applications, application_schemas and schema_attributes.
    # Existing tables are left untouched by create_all.
    Base.metadata.create_all(bind=engine)

    added_columns = add_missing_account_columns()
    created_applications, linked_accounts = backfill_applications()

    print("Application schema foundation migration complete.")
    print("Created/verified tables:")
    print("  - applications")
    print("  - application_schemas")
    print("  - schema_attributes")

    if added_columns:
        print("Added accounts columns:")
        for column_name in added_columns:
            print(f"  - {column_name}")
    else:
        print("Account schema columns were already present.")

    print(f"Backfilled application records: {created_applications}")
    print(f"Accounts linked to applications: {linked_accounts}")
    print("Existing account rows and duplicate results were preserved.")


if __name__ == "__main__":
    main()
