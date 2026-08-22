from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db_models  # noqa: F401
from app.database.base import Base
from app.db_models.integration import IntegrationRecord
from app.services.remediation_service import (
    list_decision_history,
    list_remediation_items,
    record_review_decision,
)


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    integration = IntegrationRecord(
        name="Identity Now",
        connector_type="REST",
        configuration={},
        enabled=True,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return db, integration.id


def test_confirmed_duplicate_enters_remediation_queue_and_history():
    db, integration_id = _session()

    record_review_decision(
        db,
        integration_id=integration_id,
        application="ISC",
        account_1_key="isc:1",
        account_2_key="isc:2",
        decision="DUPLICATE",
        confidence=87.0,
        reviewer_name="Reviewer",
        account_1_data={"username": "vishal.singh"},
        account_2_data={"username": "Vishal Singh"},
        source="DUPLICATE_GROUP",
    )
    db.commit()

    queue = list_remediation_items(db, status="PENDING_ACTION")
    history = list_decision_history(db)

    assert len(queue) == 1
    assert queue[0]["confidence"] == 87.0
    assert queue[0]["status"] == "PENDING_ACTION"
    assert queue[0]["account1"]["username"] == "vishal.singh"
    assert history[0]["decision"] == "DUPLICATE"
    assert history[0]["source"] == "DUPLICATE_GROUP"


def test_not_duplicate_removes_pair_from_active_remediation():
    db, integration_id = _session()

    record_review_decision(
        db,
        integration_id=integration_id,
        application="ISC",
        account_1_key="isc:1",
        account_2_key="isc:2",
        decision="DUPLICATE",
        confidence=87.0,
    )
    db.commit()

    record_review_decision(
        db,
        integration_id=integration_id,
        application="ISC",
        account_1_key="isc:1",
        account_2_key="isc:2",
        decision="NOT_DUPLICATE",
        confidence=87.0,
    )
    db.commit()

    assert list_remediation_items(db, status="PENDING_ACTION") == []
    ignored = list_remediation_items(db, status="IGNORED")
    assert len(ignored) == 1

    history = list_decision_history(db)
    assert [item["decision"] for item in history[:2]] == [
        "NOT_DUPLICATE",
        "DUPLICATE",
    ]
