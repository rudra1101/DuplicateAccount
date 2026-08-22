from sqlalchemy import select

from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.db_models.remediation_item import RemediationItemRecord
from app.db_models.review_decision_history import ReviewDecisionHistoryRecord
from app.db_models.review_pair_feedback import ReviewPairFeedbackRecord
import app.db_models  # noqa: F401


TABLES = [
    "review_decision_history",
    "remediation_items",
]


def backfill_existing_feedback() -> tuple[int, int]:
    remediation_added = 0
    history_added = 0

    with SessionLocal() as db:
        feedback_rows = list(
            db.scalars(
                select(ReviewPairFeedbackRecord).where(
                    ReviewPairFeedbackRecord.decision.in_(["DUPLICATE", "NOT_DUPLICATE"])
                )
            ).all()
        )

        for feedback in feedback_rows:
            history_exists = db.scalar(
                select(ReviewDecisionHistoryRecord.id)
                .where(
                    ReviewDecisionHistoryRecord.integration_id == feedback.integration_id,
                    ReviewDecisionHistoryRecord.application == feedback.application,
                    ReviewDecisionHistoryRecord.account_1_key == feedback.account_1_key,
                    ReviewDecisionHistoryRecord.account_2_key == feedback.account_2_key,
                    ReviewDecisionHistoryRecord.source == "PHASE10_BACKFILL",
                )
                .limit(1)
            )
            if history_exists is None:
                db.add(
                    ReviewDecisionHistoryRecord(
                        integration_id=feedback.integration_id,
                        application=feedback.application,
                        account_1_key=feedback.account_1_key,
                        account_2_key=feedback.account_2_key,
                        decision=feedback.decision,
                        confidence=None,
                        reviewer_name=feedback.reviewer_name,
                        comment=feedback.comment,
                        source="PHASE10_BACKFILL",
                        account_1_data={},
                        account_2_data={},
                    )
                )
                history_added += 1

            if feedback.decision != "DUPLICATE":
                continue

            remediation_exists = db.scalar(
                select(RemediationItemRecord.id)
                .where(
                    RemediationItemRecord.integration_id == feedback.integration_id,
                    RemediationItemRecord.application == feedback.application,
                    RemediationItemRecord.account_1_key == feedback.account_1_key,
                    RemediationItemRecord.account_2_key == feedback.account_2_key,
                )
                .limit(1)
            )
            if remediation_exists is None:
                db.add(
                    RemediationItemRecord(
                        integration_id=feedback.integration_id,
                        application=feedback.application,
                        account_1_key=feedback.account_1_key,
                        account_2_key=feedback.account_2_key,
                        account_1_data={},
                        account_2_data={},
                        confidence=None,
                        reviewer_name=feedback.reviewer_name,
                        review_comment=feedback.comment,
                        status="PENDING_ACTION",
                    )
                )
                remediation_added += 1

        db.commit()

    return remediation_added, history_added


if __name__ == "__main__":
    for table_name in TABLES:
        Base.metadata.tables[table_name].create(bind=engine, checkfirst=True)

    remediation_added, history_added = backfill_existing_feedback()
    print(
        "Phase 10 migration complete: decision history and remediation queue tables are ready. "
        f"Backfilled remediation items={remediation_added}, history records={history_added}."
    )
