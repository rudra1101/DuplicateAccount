from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_PATH = BASE_DIR / "duplicate_accounts.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        # Wait for a concurrent writer instead of immediately failing with
        # sqlite3.OperationalError: database is locked.
        "timeout": 30,
    },
    pool_pre_ping=True,
)


@event.listens_for(Engine, "connect")
def _configure_sqlite_connection(dbapi_connection, connection_record) -> None:
    """Configure SQLite for concurrent API reads and background scan writes."""
    del connection_record

    # This listener can also receive non-SQLite DBAPI connections if the
    # application changes database engines in the future.
    module_name = dbapi_connection.__class__.__module__.lower()
    if "sqlite" not in module_name:
        return

    cursor = dbapi_connection.cursor()
    try:
        # WAL allows readers (for example /api/auth/me) to continue while a
        # scan/integration transaction is writing account and result rows.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
    finally:
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI database dependency.

    Opens one SQLAlchemy session for the request and closes
    it automatically after the request finishes.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
