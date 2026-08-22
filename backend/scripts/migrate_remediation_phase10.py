from app.database.base import Base
from app.database.session import engine
import app.db_models  # noqa: F401


TABLES = [
    "review_decision_history",
    "remediation_items",
]


if __name__ == "__main__":
    for table_name in TABLES:
        Base.metadata.tables[table_name].create(bind=engine, checkfirst=True)
    print("Phase 10 migration complete: decision history and remediation queue tables are ready.")
