import pytest

import app.config as config


def test_development_defaults_are_local_and_safe(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)

    settings = config.get_runtime_settings()

    assert settings.app_env == "development"
    assert "http://localhost:5173" in settings.cors_origins
    assert "localhost" in settings.allowed_hosts
    assert settings.auth_cookie_secure is False


def test_production_rejects_unsafe_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", "short")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("ALLOWED_HOSTS", "*")
    monkeypatch.setattr(config, "IS_POSTGRESQL", False)

    settings = config.get_runtime_settings()

    with pytest.raises(RuntimeError) as exc:
        config.validate_runtime_configuration(settings)

    message = str(exc.value)
    assert "PostgreSQL" in message
    assert "AUTH_SECRET_KEY" in message
    assert "AUTH_COOKIE_SECURE" in message
    assert "CORS_ORIGINS" in message
    assert "ALLOWED_HOSTS" in message


def test_production_accepts_explicit_secure_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", "x" * 48)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "lax")
    monkeypatch.setenv("CORS_ORIGINS", "https://identity.example.com")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.identity.example.com")
    monkeypatch.setattr(config, "IS_POSTGRESQL", True)

    settings = config.get_runtime_settings()
    config.validate_runtime_configuration(settings)

    assert settings.is_production is True
    assert settings.auth_cookie_secure is True
