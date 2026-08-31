from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, and_, create_engine, delete, func, insert, select, text


BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

CHAT_ORPHAN_RELATIONSHIP = "chat_messages.conversation_id->chat_conversations.id"
KNOWLEDGE_ORPHAN_RELATIONSHIP = "knowledge_chunks.document_id->knowledge_documents.id"
SUPPORTED_ORPHAN_RELATIONSHIPS = {
    CHAT_ORPHAN_RELATIONSHIP,
    KNOWLEDGE_ORPHAN_RELATIONSHIP,
}


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


def find_source_orphans(source_engine, metadata: MetaData) -> dict[str, list[dict[str, object]]]:
    """Find simple single-column FK violations already present in a database."""
    issues: dict[str, list[dict[str, object]]] = defaultdict(list)

    with source_engine.connect() as connection:
        for child in metadata.sorted_tables:
            for fk_constraint in child.foreign_key_constraints:
                elements = list(fk_constraint.elements)
                if len(elements) != 1:
                    continue

                element = elements[0]
                child_column = element.parent
                parent_column = element.column
                parent = parent_column.table

                stmt = (
                    select(child_column, func.count().label("row_count"))
                    .select_from(child.outerjoin(parent, child_column == parent_column))
                    .where(
                        and_(
                            child_column.is_not(None),
                            parent_column.is_(None),
                        )
                    )
                    .group_by(child_column)
                )

                rows = connection.execute(stmt).mappings().all()
                if not rows:
                    continue

                key = f"{child.name}.{child_column.name}->{parent.name}.{parent_column.name}"
                issues[key].extend(dict(row) for row in rows)

    return dict(issues)


def print_source_orphans(issues: dict[str, list[dict[str, object]]]) -> None:
    if not issues:
        print("\nSource foreign-key preflight: no orphaned rows found.")
        return

    print("\nSource foreign-key preflight found legacy orphaned rows")
    print("--------------------------------------------------------")
    for relationship, rows in issues.items():
        total_rows = sum(int(row.get("row_count", 0)) for row in rows)
        print(f"{relationship}: {len(rows)} missing parent key(s), {total_rows} child row(s)")


def recover_missing_chat_conversations(
    source_engine,
    target_engine,
    source_metadata: MetaData,
    target_metadata: MetaData,
) -> int:
    """Reconstruct missing chat-conversation parents without dropping messages."""
    if "chat_messages" not in source_metadata.tables or "chat_conversations" not in source_metadata.tables:
        return 0

    source_messages = source_metadata.tables["chat_messages"]
    source_conversations = source_metadata.tables["chat_conversations"]
    target_conversations = target_metadata.tables["chat_conversations"]

    stmt = (
        select(
            source_messages.c.conversation_id,
            func.min(source_messages.c.created_at).label("first_message_at"),
            func.max(source_messages.c.created_at).label("last_message_at"),
        )
        .select_from(
            source_messages.outerjoin(
                source_conversations,
                source_messages.c.conversation_id == source_conversations.c.id,
            )
        )
        .where(source_conversations.c.id.is_(None))
        .group_by(source_messages.c.conversation_id)
    )

    with source_engine.connect() as source_connection:
        orphan_groups = source_connection.execute(stmt).mappings().all()

    if not orphan_groups:
        return 0

    payload = []
    for row in orphan_groups:
        created_at = row["first_message_at"] or datetime.utcnow()
        updated_at = row["last_message_at"] or created_at
        payload.append(
            {
                "id": row["conversation_id"],
                "title": "Recovered Conversation",
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    with target_engine.begin() as target_connection:
        target_connection.execute(insert(target_conversations), payload)

    print(
        f"chat_conversations               recovered {len(payload)} missing parent conversation(s)"
    )
    return len(payload)


def recover_missing_knowledge_documents(
    source_engine,
    target_engine,
    source_metadata: MetaData,
    target_metadata: MetaData,
) -> int:
    """Reconstruct missing knowledge-document parents without dropping chunks."""
    if "knowledge_chunks" not in source_metadata.tables or "knowledge_documents" not in source_metadata.tables:
        return 0

    source_chunks = source_metadata.tables["knowledge_chunks"]
    source_documents = source_metadata.tables["knowledge_documents"]
    target_documents = target_metadata.tables["knowledge_documents"]

    stmt = (
        select(
            source_chunks.c.document_id,
            func.count().label("chunk_count"),
            func.coalesce(func.sum(source_chunks.c.character_count), 0).label("character_count"),
            func.min(source_chunks.c.created_at).label("first_chunk_at"),
            func.max(source_chunks.c.created_at).label("last_chunk_at"),
        )
        .select_from(
            source_chunks.outerjoin(
                source_documents,
                source_chunks.c.document_id == source_documents.c.id,
            )
        )
        .where(source_documents.c.id.is_(None))
        .group_by(source_chunks.c.document_id)
    )

    with source_engine.connect() as source_connection:
        orphan_groups = source_connection.execute(stmt).mappings().all()

    if not orphan_groups:
        return 0

    payload = []
    for row in orphan_groups:
        document_id = int(row["document_id"])
        created_at = row["first_chunk_at"] or datetime.utcnow()
        updated_at = row["last_chunk_at"] or created_at
        payload.append(
            {
                "id": document_id,
                "name": f"Recovered Knowledge Document {document_id}",
                "original_filename": f"recovered-knowledge-document-{document_id}.txt",
                "content_type": "text/plain",
                "status": "READY",
                "chunk_count": int(row["chunk_count"] or 0),
                "character_count": int(row["character_count"] or 0),
                "error_message": "Parent document metadata was missing in legacy SQLite data and was reconstructed during PostgreSQL migration.",
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    with target_engine.begin() as target_connection:
        target_connection.execute(insert(target_documents), payload)

    print(
        f"knowledge_documents              recovered {len(payload)} missing parent document(s)"
    )
    return len(payload)


def reset_postgres_sequences(target_engine, metadata: MetaData) -> None:
    if target_engine.dialect.name != "postgresql":
        return

    with target_engine.begin() as connection:
        for table in metadata.sorted_tables:
            primary_keys = list(table.primary_key.columns)
            if len(primary_keys) != 1:
                continue

            column = primary_keys[0]
            try:
                python_type = column.type.python_type
            except (NotImplementedError, AttributeError):
                continue
            if python_type is not int:
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

    orphan_issues = find_source_orphans(source_engine, source_metadata)
    print_source_orphans(orphan_issues)

    unsupported_orphans = {
        relationship: rows
        for relationship, rows in orphan_issues.items()
        if relationship not in SUPPORTED_ORPHAN_RELATIONSHIPS
    }
    if unsupported_orphans:
        raise RuntimeError(
            "Source contains foreign-key orphan(s) that require explicit repair before migration: "
            + ", ".join(sorted(unsupported_orphans))
        )

    target_counts_before = row_counts(target_engine, target_metadata)
    populated_target_tables = {
        name: count
        for name, count in target_counts_before.items()
        if name != "alembic_version" and count > 0
    }
    if populated_target_tables and not truncate_target:
        details = ", ".join(
            f"{name}={count}" for name, count in sorted(populated_target_tables.items())
        )
        raise RuntimeError(
            "PostgreSQL already contains partially migrated application data ("
            + details
            + "). Re-run with --execute --truncate-target to restart the copy safely."
        )

    if truncate_target:
        print("\nClearing target tables in reverse dependency order...")
        with target_engine.begin() as target_connection:
            for source_table in reversed(source_metadata.sorted_tables):
                target_table = target_metadata.tables[source_table.name]
                target_connection.execute(delete(target_table))

    print("\nCopying rows...")
    recovered_chat_conversations = 0
    recovered_knowledge_documents = 0

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

            if source_table.name == "chat_conversations":
                recovered_chat_conversations = recover_missing_chat_conversations(
                    source_engine,
                    target_engine,
                    source_metadata,
                    target_metadata,
                )
            elif source_table.name == "knowledge_documents":
                recovered_knowledge_documents = recover_missing_knowledge_documents(
                    source_engine,
                    target_engine,
                    source_metadata,
                    target_metadata,
                )

    reset_postgres_sequences(target_engine, target_metadata)

    target_counts = row_counts(target_engine, target_metadata)
    print_counts("PostgreSQL target counts", target_counts)

    expected_counts = dict(source_counts)
    if recovered_chat_conversations:
        expected_counts["chat_conversations"] += recovered_chat_conversations
        print(
            "\nValidation note: chat_conversations target includes "
            f"{recovered_chat_conversations} recovered parent row(s) required to preserve orphaned SQLite chat messages."
        )
    if recovered_knowledge_documents:
        expected_counts["knowledge_documents"] += recovered_knowledge_documents
        print(
            "Validation note: knowledge_documents target includes "
            f"{recovered_knowledge_documents} recovered parent row(s) required to preserve orphaned SQLite knowledge chunks."
        )

    mismatches = {
        table: (expected_counts[table], target_counts.get(table, -1))
        for table in expected_counts
        if expected_counts[table] != target_counts.get(table)
    }

    if mismatches:
        print("\nROW COUNT VALIDATION FAILED")
        for table, (expected_count, target_count) in mismatches.items():
            print(f"{table}: expected={expected_count}, target={target_count}")
        raise SystemExit(2)

    post_migration_orphans = find_source_orphans(target_engine, target_metadata)
    if post_migration_orphans:
        print_source_orphans(post_migration_orphans)
        raise RuntimeError("PostgreSQL foreign-key validation found orphaned rows after migration.")

    print("\nRow-count validation passed for every migrated table.")
    print("PostgreSQL foreign-key validation passed.")


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
    print_source_orphans(find_source_orphans(source_engine, source_metadata))

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
