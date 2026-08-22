from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db_models  # noqa: F401
from app.database.base import Base
from app.db_models.integration import IntegrationRecord
from app.db_models.review_candidate import ReviewCandidateRecord
from app.db_models.scan import ScanRecord
from app.services.reviewer_analytics_service import get_reviewer_feedback_analytics


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
    db.flush()

    scan = ScanRecord(
        integration_id=integration.id,
        filename="phase11d",
        status="COMPLETED",
    )
    db.add(scan)
    db.flush()
    return db, scan.id


def _candidate(scan_id: int, candidate_id: int, decision: str, *, email_exact: bool):
    return ReviewCandidateRecord(
        id=candidate_id,
        scan_id=scan_id,
        application="ISC",
        account_1_key=f"isc:{candidate_id}:a",
        account_2_key=f"isc:{candidate_id}:b",
        confidence=90.0,
        review_reason="TEST",
        features={
            "email_exact": email_exact,
            "username_similarity": 0.95,
            "display_name_similarity": 0.94,
            "dynamic_identifier_matches": 1,
            "dynamic_identifier_conflicts": 0,
        },
        matched_attributes=[
            "employeeNumber",
            "Username Similarity (93.3%)",
            "Email Exact" if email_exact else "Email Similarity (93.8%)",
        ],
        review_decision=decision,
    )


def test_evidence_performance_uses_reviewer_decisions():
    db, scan_id = _session()
    db.add(_candidate(scan_id, 1, "DUPLICATE", email_exact=True))
    db.add(_candidate(scan_id, 2, "NOT_DUPLICATE", email_exact=True))
    db.commit()

    analytics = get_reviewer_feedback_analytics(db)
    rows = {row["evidence"]: row for row in analytics["evidencePerformance"]}

    assert rows["Email exact"]["reviewed"] == 2
    assert rows["Email exact"]["confirmedDuplicates"] == 1
    assert rows["Email exact"]["notDuplicates"] == 1
    assert rows["Email exact"]["confirmationRate"] == 50.0
    assert rows["Email exact"]["falsePositiveRate"] == 50.0
    assert rows["Email exact"]["sampleQuality"] == "LIMITED"


def test_evidence_patterns_capture_signal_combinations():
    db, scan_id = _session()
    db.add(_candidate(scan_id, 1, "DUPLICATE", email_exact=True))
    db.commit()

    analytics = get_reviewer_feedback_analytics(db)
    patterns = analytics["evidencePatterns"]

    assert len(patterns) >= 1
    assert any("Email exact" in row["evidence"] for row in patterns)
    assert any("Strong name similarity" in row["evidence"] for row in patterns)


def test_profiled_similarity_labels_are_bucketed_instead_of_fragmented():
    db, scan_id = _session()
    db.add(_candidate(scan_id, 1, "NOT_DUPLICATE", email_exact=False))
    db.commit()

    analytics = get_reviewer_feedback_analytics(db)
    labels = {row["evidence"] for row in analytics["evidencePerformance"]}

    assert "Profiled username similarity (90-94%)" in labels
    assert "Profiled email similarity (90-94%)" in labels
    assert "Profiled attribute: Username Similarity (93.3%)" not in labels
    assert "Profiled attribute: Email Similarity (93.8%)" not in labels


def test_evidence_family_analytics_group_correlated_identity_fields():
    db, scan_id = _session()
    db.add(_candidate(scan_id, 1, "DUPLICATE", email_exact=True))
    db.add(_candidate(scan_id, 2, "NOT_DUPLICATE", email_exact=False))
    db.commit()

    analytics = get_reviewer_feedback_analytics(db)
    families = {row["evidence"]: row for row in analytics["evidenceFamilyPerformance"]}

    assert "Authoritative Identifier" in families
    assert "Name" in families
    assert "Account Handle" in families
    assert families["Account Handle"]["reviewed"] == 2
    assert families["Account Handle"]["usableSamples"] == 2
