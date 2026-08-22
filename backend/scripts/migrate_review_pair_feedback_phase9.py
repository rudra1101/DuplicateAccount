from app.database.session import engine
from app.db_models.review_pair_feedback import ReviewPairFeedbackRecord


def main() -> None:
    ReviewPairFeedbackRecord.__table__.create(bind=engine, checkfirst=True)
    print("Phase 9 migration complete: review_pair_feedback table is ready.")


if __name__ == "__main__":
    main()
