from app.db_models.review_candidate import ReviewCandidateRecord
from app.services.review_candidate_repository import (
    save_review_candidate_decision,
    save_review_candidates,
)


class FakeSession:
    def __init__(self, record=None):
        self.added = []
        self.commits = 0
        self.record = record

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def get(self, model, candidate_id):
        assert model is ReviewCandidateRecord
        if self.record is not None and self.record.id == candidate_id:
            return self.record
        return None

    def refresh(self, value):
        return None


def test_standalone_review_candidate_is_persisted_without_group_id():
    db = FakeSession()
    saved = save_review_candidates(
        db,
        scan_id=101,
        candidates=[
            {
                "account1Key": "isc:1",
                "account2Key": "isc:2",
                "account1": {"id": "1", "application": "ISC", "username": "john.smith1"},
                "account2": {"id": "2", "application": "ISC", "username": "john.smith2"},
                "confidence": 44.0,
                "classification": "WEAK_MATCH",
                "reviewReason": "STRONG_NAME_WITH_USERNAME_SUPPORT",
                "features": {"username_similarity": 0.8571},
            }
        ],
    )

    assert saved == 1
    assert db.commits == 1
    assert len(db.added) == 1
    record = db.added[0]
    assert isinstance(record, ReviewCandidateRecord)
    assert record.scan_id == 101
    assert record.application == "ISC"
    assert record.confidence == 44.0
    assert record.review_reason == "STRONG_NAME_WITH_USERNAME_SUPPORT"
    assert not hasattr(record, "group_id")


def test_standalone_review_candidate_accepts_existing_review_decisions():
    record = ReviewCandidateRecord(
        scan_id=101,
        application="ISC",
        account_1_key="isc:1",
        account_2_key="isc:2",
        account_1_data={},
        account_2_data={},
        confidence=40.21,
        review_reason="MULTI_SIGNAL_IDENTITY_REVIEW",
    )
    record.id = 7
    db = FakeSession(record=record)

    result = save_review_candidate_decision(
        db,
        candidate_id=7,
        decision="UNCERTAIN",
        comment="Needs application owner review",
        reviewer_name="Reviewer",
    )

    assert result["reviewDecision"] == "UNCERTAIN"
    assert result["reviewComment"] == "Needs application owner review"
    assert result["reviewerName"] == "Reviewer"
    assert result["reviewedAt"] is not None
    assert db.commits == 1
