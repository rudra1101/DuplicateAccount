from __future__ import annotations

import os
from dataclasses import dataclass

from app.database.session import IS_POSTGRESQL


LOCAL_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def _csv_env(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    raw = str(os.getenv(name, "") or "").strip()
    if not raw:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _bool_env(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RuntimeSettings:
    app_env: str
    cors_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    auth_cookie_secure: bool
    auth_cookie_samesite: str
    security_headers_enabled: bool

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def get_runtime_settings() -> RuntimeSettings:
    app_env = str(os.getenv("APP_ENV", "development") or "development").strip().lower()
    default_origins = LOCAL_CORS_ORIGINS if app_env != "production" else ()
    default_hosts = ("localhost", "127.0.0.1", "testserver") if app_env != "production" else ()

    same_site = str(os.getenv("AUTH_COOKIE_SAMESITE", "lax") or "lax").strip().lower()
    if same_site not in {"lax", "strict", "none"}:
        raise RuntimeError("AUTH_COOKIE_SAMESITE must be lax, strict, or none.")

    return RuntimeSettings(
        app_env=app_env,
        cors_origins=_csv_env("CORS_ORIGINS", default_origins),
        allowed_hosts=_csv_env("ALLOWED_HOSTS", default_hosts),
        auth_cookie_secure=_bool_env("AUTH_COOKIE_SECURE", default=app_env == "production"),
        auth_cookie_samesite=same_site,
        security_headers_enabled=_bool_env("SECURITY_HEADERS_ENABLED", default=True),
    )


def validate_runtime_configuration(settings: RuntimeSettings) -> None:
    """Fail fast when production configuration is unsafe or incomplete."""
    if not settings.is_production:
        return

    problems: list[str] = []
    secret = str(os.getenv("AUTH_SECRET_KEY", "") or "").strip()

    if not IS_POSTGRESQL:
        problems.append("DATABASE_URL must use PostgreSQL in production")

    if len(secret) < 32:
        problems.append("AUTH_SECRET_KEY must contain at least 32 characters in production")

    if not settings.auth_cookie_secure:
        problems.append("AUTH_COOKIE_SECURE must be true in production")

    if settings.auth_cookie_samesite == "none" and not settings.auth_cookie_secure:
        problems.append("SameSite=None requires secure authentication cookies")

    # Same-origin deployments behind a reverse proxy do not require CORS at all.
    # When origins are configured, keep them explicit and production-safe.
    if any(origin == "*" or "localhost" in origin or "127.0.0.1" in origin for origin in settings.cors_origins):
        problems.append("CORS_ORIGINS must not use wildcard or localhost origins in production")

    if not settings.allowed_hosts:
        problems.append("ALLOWED_HOSTS must contain at least one production hostname")
    elif "*" in settings.allowed_hosts:
        problems.append("ALLOWED_HOSTS must not use wildcard in production")

    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
