from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
from app.db_models.account import AccountRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.orphan_finding import OrphanFindingRecord
from app.db_models.orphan_state import OrphanStateRecord
from app.db_models.scan import ScanRecord
from app.db_models.source_account import SourceAccountRecord
from app.services.orphan_state_service import reconcile_orphan_states


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(IntegrationRecord(id=1, name="AD", connector_type="LOCAL_FILE", source_purpose="ACCOUNT", configuration={}, enabled=True))
    db.commit()
    return db


def _seed_scan(db: Session, scan_id: int) -> tuple[ScanRecord, AccountRecord]:
    scan = ScanRecord(id=scan_id, integration_id=1, filename=f"scan-{scan_id}.csv", status="COMPLETED")
    account = AccountRecord(
        scan_id=scan_id,
        source_account_id="guid-1",
        application="Active Directory",
        username="rshankar",
        display_name="Rudra Shankar",
        email="rudra@example.com",
        employee_id="W00001",
        raw_attributes={"objectGUID": "guid-1", "employeeID": "W00001"},
    )
    db.add(scan)
    db.add(account)
    db.commit()
    db.refresh(account)
    return scan, account


def test_orphan_state_is_created_and_later_resolved():
    db = _session()
    try:
        now = datetime.now(UTC)
        db.add(SourceAccountRecord(
            integration_id=1,
            application="Active Directory",
            native_identity="guid-1",
            username="rshankar",
            display_name="Rudra Shankar",
            email="rudra@example.com",
            employee_id="W00001",
            raw_attributes={"objectGUID": "guid-1", "employeeID": "W00001"},
            attribute_fingerprint="a" * 64,
            active=True,
            deleted=False,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        ))
        db.commit()

        _, account = _seed_scan(db, 1)
        finding = OrphanFindingRecord(
            scan_id=1,
            account_id=account.id,
            orphan_type="UNMATCHED_ACCOUNT",
            evidence={"reason": "No configured correlation rule matched an authoritative identity."},
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)

        stats = reconcile_orphan_states(db, scan_id=1, findings=[finding])
        state = db.scalar(select(OrphanStateRecord))
        assert stats["created"] == 1
        assert state is not None
        assert state.active is True
        assert state.status == "OPEN"
        assert state.orphan_type == "UNMATCHED_ACCOUNT"

        _seed_scan(db, 2)
        stats = reconcile_orphan_states(db, scan_id=2, findings=[])
        db.refresh(state)
        assert stats["resolved"] == 1
        assert state.active is False
        assert state.status == "RESOLVED"
    finally:
        db.close()
