from collections.abc import Generator
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import Session, sessionmaker


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

# Load the backend environment file explicitly so database configuration does
# not depend on the directory from which Uvicorn/pytest was started.
load_dotenv(ENV_FILE)


def _resolve_sqlite_database_path() -> Path:
    """Resolve the legacy SQLite runtime path.

    IDENTITYAI_DATABASE_PATH is kept for backward compatibility while the
    application transitions to DATABASE_URL. If DATABASE_URL is not supplied,
    the existing SQLite database remains the default.
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


def _default_sqlite_url() -> str:
    path = _resolve_sqlite_database_path()
    return f"sqlite:///{path.as_posix()}"


def _structured_database_url() -> str | None:
    """Build a PostgreSQL URL from separate environment values when requested.

    Containers can set DATABASE_HOST to opt into this path. Keeping the password
    separate avoids manual URL encoding problems for characters such as @, :, /
    and #. Local development continues to use DATABASE_URL unchanged when no
    structured host override is present.
    """
    host = str(os.getenv("DATABASE_HOST", "") or "").strip()
    if not host:
        return None

    username = str(os.getenv("DATABASE_USER", "") or "").strip()
    password = str(os.getenv("DATABASE_PASSWORD", "") or "")
    database = str(os.getenv("DATABASE_NAME", "") or "").strip()
    port_raw = str(os.getenv("DATABASE_PORT", "5432") or "5432").strip()

    if not username:
        raise RuntimeError("DATABASE_USER is required when DATABASE_HOST is configured.")
    if not database:
        raise RuntimeError("DATABASE_NAME is required when DATABASE_HOST is configured.")
    if not password:
        raise RuntimeError("DATABASE_PASSWORD is required when DATABASE_HOST is configured.")

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise RuntimeError("DATABASE_PORT must be an integer.") from exc

    return URL.create(
        drivername="postgresql+psycopg",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    ).render_as_string(hide_password=False)


def _resolve_database_url() -> str:
    structured_url = _structured_database_url()
    if structured_url:
        return structured_url

    configured_url = str(os.getenv("DATABASE_URL", "") or "").strip()
    return configured_url or _default_sqlite_url()


DATABASE_URL = _resolve_database_url()
DATABASE_BACKEND = make_url(DATABASE_URL).get_backend_name()
IS_SQLITE = DATABASE_BACKEND == "sqlite"
IS_POSTGRESQL = DATABASE_BACKEND == "postgresql"


engine_options: dict[str, object] = {
    "pool_pre_ping": True,
}

if IS_SQLITE:
    engine_options["connect_args"] = {
        "check_same_thread": False,
        # Wait for a concurrent writer instead of immediately failing with
        # sqlite3.OperationalError: database is locked.
        "timeout": 30,
    }
else:
    # PostgreSQL and other network databases use SQLAlchemy's normal pooled
    # connections. Keep stale connections from lingering indefinitely.
    engine_options.update(
        {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
        }
    )


engine = create_engine(
    DATABASE_URL,
    **engine_options,
)


@event.listens_for(Engine, "connect")
def _configure_database_connection(dbapi_connection, connection_record) -> None:
    """Apply connection-local settings only when the driver is SQLite."""
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
