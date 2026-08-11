from __future__ import annotations

import sqlite3
from pathlib import Path


DATABASE_PATH = Path(
    "duplicate_accounts.db"
)


def column_exists(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    column_name: str,
) -> bool:
    cursor = connection.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = {
        row[1]
        for row in cursor.fetchall()
    }

    return column_name in columns


def index_exists(
    connection: sqlite3.Connection,
    *,
    index_name: str,
) -> bool:
    cursor = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'index'
        AND name = ?
        """,
        (index_name,),
    )

    return cursor.fetchone() is not None


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "Database was not found: "
            f"{DATABASE_PATH.resolve()}"
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:
        if not column_exists(
            connection,
            table_name="scans",
            column_name="integration_id",
        ):
            connection.execute(
                """
                ALTER TABLE scans
                ADD COLUMN integration_id INTEGER
                REFERENCES integrations(id)
                ON DELETE SET NULL
                """
            )

            print(
                "Added scans.integration_id."
            )
        else:
            print(
                "scans.integration_id "
                "already exists."
            )

        index_name = (
            "ix_scans_integration_id"
        )

        if not index_exists(
            connection,
            index_name=index_name,
        ):
            connection.execute(
                """
                CREATE INDEX
                ix_scans_integration_id
                ON scans(integration_id)
                """
            )

            print(
                "Created integration index."
            )
        else:
            print(
                "Integration index "
                "already exists."
            )

        connection.commit()

        columns = connection.execute(
            "PRAGMA table_info(scans)"
        ).fetchall()

        print(
            "\nCurrent scans columns:"
        )

        for column in columns:
            print(
                f"- {column[1]} "
                f"({column[2]})"
            )

        print(
            "\nMigration completed."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()