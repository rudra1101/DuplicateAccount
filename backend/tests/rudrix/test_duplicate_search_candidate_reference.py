from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.db_models.account import AccountRecord
from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.scan import ScanRecord
from app.ai.tools.account_resolution_tools import GroundedSearchDuplicateGroupsTool


def test_duplicate_search_matches_employee_id_on_candidate_account():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        integration = IntegrationRecord(name="Active Directory", connector_type="AD")
        db.add(integration)
        db.flush()

        scan = ScanRecord(integration_id=integration.id, status="COMPLETED")
        db.add(scan)
        db.flush()

        primary = AccountRecord(
            scan_id=scan.id,
            application="Active Directory",
            username="asinha.legacy",
            display_name="Aditya Sinha Legacy",
            email="asinha.legacy@examplecorp.com",
            employee_id="LEGACY03",
        )
        duplicate = AccountRecord(
            scan_id=scan.id,
            application="Active Directory",
            username="asinha",
            display_name="Aditya Sinha",
            email="asinha@examplecorp.com",
            employee_id="W00003",
        )
        db.add_all([primary, duplicate])
        db.flush()

        group = DuplicateGroupRecord(
            scan_id=scan.id,
            application="Active Directory",
            primary_username="asinha.legacy",
            duplicate_count=1,
            highest_confidence=97,
        )
        db.add(group)
        db.flush()

        candidate = DuplicateCandidateRecord(
            group_id=group.id,
            candidate_number=1,
            username="asinha",
            confidence=97,
            recommendation="REVIEW",
            account_data={
                "username": "asinha",
                "displayName": "Aditya Sinha",
                "email": "asinha@examplecorp.com",
                "employeeId": "W00003",
            },
        )
        db.add(candidate)
        db.commit()

        result = GroundedSearchDuplicateGroupsTool().execute(
            db=db,
            arguments={
                "integration": None,
                "application": None,
                "minimum_confidence": 0,
                "search": "W00003",
                "limit": 20,
            },
        )

        assert result["found"] is True
        assert result["totalMatchingGroups"] == 1
        assert result["groups"][0]["groupId"] == group.id
        assert result["groups"][0]["candidates"][0]["username"] == "asinha"
