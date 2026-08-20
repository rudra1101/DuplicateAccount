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


def main() -> None:
    # Creates applications, application_schemas and schema_attributes.
    # Existing tables are left untouched by create_all.
    Base.metadata.create_all(bind=engine)

    added_columns = add_missing_account_columns()

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

    print("Existing account data was not modified or deleted.")


if __name__ == "__main__":
    main()
