import pytest
from sqlalchemy.engine import make_url

from app.database import session


def test_structured_database_url_safely_handles_special_password_characters(monkeypatch):
    monkeypatch.setenv("DATABASE_HOST", "postgres")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("DATABASE_NAME", "identityai")
    monkeypatch.setenv("DATABASE_USER", "identityai")
    monkeypatch.setenv("DATABASE_PASSWORD", "p@ss:/#word")

    value = session._structured_database_url()

    assert value is not None
    parsed = make_url(value)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "postgres"
    assert parsed.port == 5432
    assert parsed.database == "identityai"
    assert parsed.username == "identityai"
    assert parsed.password == "p@ss:/#word"


def test_structured_database_url_requires_complete_credentials(monkeypatch):
    monkeypatch.setenv("DATABASE_HOST", "postgres")
    monkeypatch.setenv("DATABASE_NAME", "identityai")
    monkeypatch.setenv("DATABASE_USER", "identityai")
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_PASSWORD"):
        session._structured_database_url()
