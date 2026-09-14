from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
from app.db_models.source_account import SourceAccountRecord
from app.services.source_account_inventory_service import normalize_aggregation_type, upsert_source_accounts


def _account(native_id: str, username: str) -> dict:
    return {
        "id": native_id,
        "application": "Test App",
        "username": username,
        "rawAttributes": {"nativeId": native_id, "username": username},
    }


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_aggregation_type_validation():
    assert normalize_aggregation_type(None) == "FULL"
    assert normalize_aggregation_type("full") == "FULL"
    assert normalize_aggregation_type("delta") == "DELTA"


def test_delta_does_not_delete_accounts_missing_from_batch():
    db = _session()
    try:
        upsert_source_accounts(
            db,
            integration_id=1,
            accounts=[_account("A1", "one"), _account("A2", "two")],
            scan_id=None,
            aggregation_type="FULL",
        )
        stats = upsert_source_accounts(
            db,
            integration_id=1,
            accounts=[_account("A1", "one-updated")],
            scan_id=None,
            aggregation_type="DELTA",
        )
        rows = list(db.scalars(select(SourceAccountRecord).order_by(SourceAccountRecord.native_identity)).all())
        assert stats["updated"] == 1
        assert stats["deleted"] == 0
        assert len(rows) == 2
        assert rows[1].native_identity == "A2"
        assert rows[1].active is True
        assert rows[1].deleted is False
    finally:
        db.close()


def test_full_marks_accounts_missing_from_snapshot_deleted():
    db = _session()
    try:
        upsert_source_accounts(
            db,
            integration_id=1,
            accounts=[_account("A1", "one"), _account("A2", "two")],
            scan_id=None,
            aggregation_type="FULL",
        )
        stats = upsert_source_accounts(
            db,
            integration_id=1,
            accounts=[_account("A1", "one")],
            scan_id=None,
            aggregation_type="FULL",
        )
        rows = list(db.scalars(select(SourceAccountRecord).order_by(SourceAccountRecord.native_identity)).all())
        assert stats["deleted"] == 1
        assert rows[1].native_identity == "A2"
        assert rows[1].active is False
        assert rows[1].deleted is True
    finally:
        db.close()
