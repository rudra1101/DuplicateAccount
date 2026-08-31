from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine, delete, func, insert, select, text


BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy IdentityAI data from SQLite to PostgreSQL and validate row counts."
    )
    parser.add_argument(
        "--source",
        default=f"sqlite:///{(BACKEND_DIR / 'duplicate_accounts.db').as_posix()}",
        help="Source SQLite SQLAlchemy URL.",
    )
    parser.add_argument(
        "--target",
        default=os.getenv("DATABASE_URL", ""),
        help="Target PostgreSQL SQLAlchemy URL. Defaults to DATABASE_URL.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually copy rows. Without this flag the script only inspects/validates.",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Delete existing target rows before copying. Only valid with --execute.",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    return parser.parse_args()


def row_counts(engine, metadata: MetaData) -> dict[str, int]:
    result: dict[str, int] = {}
    with engine.connect() as connection:
        for table in metadata.sorted_tables:
            result[table.name] = int(
                connection.scalar(select(func.count()).select_from(table)) or 0
            )
    return result


def print_counts(title: str, counts: dict[str, int]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for table_name, count in counts.items():
        print(f"{table_name:32} {count:>10}")


def reset_postgres_sequences(target_engine, metadata: MetaData) -> None:
    if target_engine.dialect.name != "postgresql":
        return

    with target_engine.begin() as connection:
        for table in metadata.sorted_tables:
            primary_keys = list(table.primary_key.columns)
            if len(primary_keys) != 1:
                continue

            column = primary_keys[0]
            if not getattr(column.type, "python_type", None) is int:
                continue

            sequence_name = connection.scalar(
                text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
                {"table_name": table.name, "column_name": column.name},
            )
            if not sequence_name:
                continue

            max_id = connection.scalar(select(func.max(column)))
            if max_id is None:
                connection.execute(
                    text("SELECT setval(CAST(:sequence_name AS regclass), 1, false)"),
                    {"sequence_name": sequence_name},
                )
            else:
                connection.execute(
                    text("SELECT setval(CAST(:sequence_name AS regclass), :max_id, true)"),
                    {"sequence_name": sequence_name, "max_id": int(max_id)},
                )


def migrate(source_engine, target_engine, batch_size: int, truncate_target: bool) -> None:
    source_metadata = MetaData()
    source_metadata.reflect(bind=source_engine)

    target_metadata = MetaData()
    target_metadata.reflect(bind=target_engine)

    missing_tables = [
        table.name
        for table in source_metadata.sorted_tables
        if table.name not in target_metadata.tables
    ]
    if missing_tables:
        raise RuntimeError(
            "Target schema is missing tables: " + ", ".join(missing_tables)
        )

    source_counts = row_counts(source_engine, source_metadata)
    print_counts("SQLite source counts", source_counts)

    if truncate_target:
        print("\nClearing target tables in reverse dependency order...")
        with target_engine.begin() as target_connection:
            for source_table in reversed(source_metadata.sorted_tables):
                target_table = target_metadata.tables[source_table.name]
                target_connection.execute(delete(target_table))

    print("\nCopying rows...")
    with source_engine.connect() as source_connection:
        for source_table in source_metadata.sorted_tables:
            target_table = target_metadata.tables[source_table.name]
            total = source_counts[source_table.name]
            copied = 0

            result = source_connection.execution_options(stream_results=True).execute(
                select(source_table)
            )

            while True:
                rows = result.mappings().fetchmany(batch_size)
                if not rows:
                    break

                payload = [dict(row) for row in rows]
                with target_engine.begin() as target_connection:
                    target_connection.execute(insert(target_table), payload)
                copied += len(payload)

            print(f"{source_table.name:32} copied {copied}/{total}")

    reset_postgres_sequences(target_engine, target_metadata)

    target_counts = row_counts(target_engine, target_metadata)
    print_counts("PostgreSQL target counts", target_counts)

    mismatches = {
        table: (source_counts[table], target_counts.get(table, -1))
        for table in source_counts
        if source_counts[table] != target_counts.get(table)
    }

    if mismatches:
        print("\nROW COUNT VALIDATION FAILED")
        for table, (source_count, target_count) in mismatches.items():
            print(f"{table}: source={source_count}, target={target_count}")
        raise SystemExit(2)

    print("\nRow-count validation passed for every migrated table.")


def main() -> None:
    args = parse_args()

    if not args.target:
        raise SystemExit(
            "Target database is not configured. Set DATABASE_URL or pass --target."
        )
    if not args.target.startswith("postgresql"):
        raise SystemExit("Target must be a PostgreSQL SQLAlchemy URL.")
    if args.truncate_target and not args.execute:
        raise SystemExit("--truncate-target requires --execute.")

    source_engine = create_engine(args.source)
    target_engine = create_engine(args.target, pool_pre_ping=True)

    source_metadata = MetaData()
    source_metadata.reflect(bind=source_engine)
    print_counts("SQLite source counts", row_counts(source_engine, source_metadata))

    target_metadata = MetaData()
    target_metadata.reflect(bind=target_engine)
    print_counts("Current PostgreSQL target counts", row_counts(target_engine, target_metadata))

    if not args.execute:
        print(
            "\nDRY RUN ONLY. No data was changed. "
            "Re-run with --execute after validating the source/target databases."
        )
        return

    migrate(
        source_engine=source_engine,
        target_engine=target_engine,
        batch_size=max(1, args.batch_size),
        truncate_target=args.truncate_target,
    )


if __name__ == "__main__":
    main()
