from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.review_pair_feedback import ReviewPairFeedbackRecord


DURABLE_FEEDBACK_DECISIONS = {"DUPLICATE", "NOT_DUPLICATE"}


def normalize_pair_keys(account_1_key: str, account_2_key: str) -> tuple[str, str]:
    return tuple(sorted((str(account_1_key), str(account_2_key))))


def upsert_pair_feedback(
    db: Session,
    *,
    integration_id: int,
    application: str,
    account_1_key: str,
    account_2_key: str,
    decision: str,
    comment: str | None = None,
    reviewer_name: str | None = None,
    source_review_candidate_id: int | None = None,
) -> ReviewPairFeedbackRecord | None:
    normalized = decision.strip().upper()
    key_1, key_2 = normalize_pair_keys(account_1_key, account_2_key)

    existing = db.scalar(
        select(ReviewPairFeedbackRecord).where(
            ReviewPairFeedbackRecord.integration_id == integration_id,
            ReviewPairFeedbackRecord.application == application,
            ReviewPairFeedbackRecord.account_1_key == key_1,
            ReviewPairFeedbackRecord.account_2_key == key_2,
        )
    )

    if normalized not in DURABLE_FEEDBACK_DECISIONS:
        if existing is not None:
            db.delete(existing)
        return None

    if existing is None:
        existing = ReviewPairFeedbackRecord(
            integration_id=integration_id,
            application=application,
            account_1_key=key_1,
            account_2_key=key_2,
            decision=normalized,
        )
        db.add(existing)

    existing.decision = normalized
    existing.comment = (comment or "").strip() or None
    existing.reviewer_name = (reviewer_name or "").strip() or None
    existing.source_review_candidate_id = source_review_candidate_id
    return existing


def load_pair_feedback(
    db: Session,
    *,
    integration_id: int,
) -> dict[tuple[str, str, str], str]:
    records = list(
        db.scalars(
            select(ReviewPairFeedbackRecord).where(
                ReviewPairFeedbackRecord.integration_id == integration_id,
            )
        ).all()
    )

    return {
        (record.application, record.account_1_key, record.account_2_key): record.decision
        for record in records
    }
