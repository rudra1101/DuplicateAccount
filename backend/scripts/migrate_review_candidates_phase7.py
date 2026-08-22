from app.database.session import engine
from app.db_models.review_candidate import ReviewCandidateRecord


def main() -> None:
    ReviewCandidateRecord.__table__.create(bind=engine, checkfirst=True)
    print("Phase 7 migration complete: review_candidates table is ready.")


if __name__ == "__main__":
    main()
