from collections.abc import Generator
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _resolve_database_path() -> Path:
    """Resolve the SQLite runtime path.

    IDENTITYAI_DATABASE_PATH can point to a database outside the repository
    (recommended when the project lives in OneDrive/Dropbox/other synced
    folders). If it is not set, preserve the existing repository-local path so
    current installations continue to work unchanged.
    """
    configured_path = str(
        os.getenv("IDENTITYAI_DATABASE_PATH", "")
        or ""
    ).strip()

    if configured_path:
        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
    else:
        path = BASE_DIR / "duplicate_accounts.db"

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


DATABASE_PATH = _resolve_database_path()
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
    """Configure connection-local SQLite settings safely.

    Do not execute PRAGMA journal_mode=WAL here. Changing journal mode is a
    database-wide operation that can itself require an exclusive lock. Running
    it for every pooled connection can therefore prevent the application from
    starting when another process has the database open.
    """
    del connection_record

    module_name = dbapi_connection.__class__.__module__.lower()
    if "sqlite" not in module_name:
        return

    cursor = dbapi_connection.cursor()
    try:
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
    """FastAPI database dependency."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
