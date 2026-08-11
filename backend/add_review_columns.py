import sqlite3
from pathlib import Path


DATABASE_PATH = Path("duplicate_accounts.db")
# Change this if your SQLite filename is different.


COLUMNS = {
    "review_decision": "VARCHAR(30)",
    "review_comment": "TEXT",
    "reviewer_name": "VARCHAR(255)",
    "reviewed_at": "DATETIME",
}


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH.resolve()}"
        )

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute(
        "PRAGMA table_info(duplicate_candidates)"
    )

    existing_columns = {
        row[1]
        for row in cursor.fetchall()
    }

    for column_name, column_type in COLUMNS.items():
        if column_name in existing_columns:
            print(
                f"Skipping existing column: {column_name}"
            )
            continue

        cursor.execute(
            f"""
            ALTER TABLE duplicate_candidates
            ADD COLUMN {column_name} {column_type}
            """
        )

        print(
            f"Added column: {column_name}"
        )

    connection.commit()
    connection.close()

    print("Migration completed successfully.")


if __name__ == "__main__":
    main()