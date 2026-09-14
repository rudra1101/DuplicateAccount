from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
from app.db_models.identity import IdentityRecord
from app.db_models.integration import IntegrationRecord
from app.services.identity_ingestion_service import upsert_authoritative_identities


def _identity(native_id: str, username: str) -> dict:
    return {
        "id": native_id,
        "application": "HR",
        "username": username,
        "status": "ACTIVE",
        "rawAttributes": {"workerId": native_id, "username": username},
    }


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(
        IntegrationRecord(
            id=1,
            name="HR Test Source",
            connector_type="LOCAL_FILE",
            source_purpose="AUTHORITATIVE",
            configuration={},
            enabled=True,
        )
    )
    db.commit()
    return db


def test_delta_keeps_authoritative_identities_missing_from_batch_active():
    db = _session()
    try:
        upsert_authoritative_identities(
            db,
            integration_id=1,
            identities=[_identity("W1", "one"), _identity("W2", "two")],
            aggregation_type="FULL",
        )
        rows = list(db.scalars(select(IdentityRecord).order_by(IdentityRecord.source_identity_id)).all())
        original_id = rows[0].id

        stats = upsert_authoritative_identities(
            db,
            integration_id=1,
            identities=[_identity("W1", "one-updated")],
            aggregation_type="DELTA",
        )
        rows = list(db.scalars(select(IdentityRecord).order_by(IdentityRecord.source_identity_id)).all())

        assert stats["updated"] == 1
        assert stats["deleted"] == 0
        assert rows[0].id == original_id
        assert rows[0].username == "one-updated"
        assert rows[1].source_identity_id == "W2"
        assert rows[1].active is True
        assert rows[1].deleted is False
    finally:
        db.close()


def test_full_marks_missing_authoritative_identity_deleted_without_removing_row():
    db = _session()
    try:
        upsert_authoritative_identities(
            db,
            integration_id=1,
            identities=[_identity("W1", "one"), _identity("W2", "two")],
            aggregation_type="FULL",
        )
        before = list(db.scalars(select(IdentityRecord).order_by(IdentityRecord.source_identity_id)).all())
        w2_id = before[1].id

        stats = upsert_authoritative_identities(
            db,
            integration_id=1,
            identities=[_identity("W1", "one")],
            aggregation_type="FULL",
        )
        rows = list(db.scalars(select(IdentityRecord).order_by(IdentityRecord.source_identity_id)).all())

        assert stats["deleted"] == 1
        assert len(rows) == 2
        assert rows[1].id == w2_id
        assert rows[1].source_identity_id == "W2"
        assert rows[1].active is False
        assert rows[1].deleted is True
    finally:
        db.close()
