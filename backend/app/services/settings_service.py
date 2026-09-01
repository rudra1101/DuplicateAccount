from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.db_models.application_settings import ApplicationSettingsRecord


@dataclass(frozen=True)
class SmtpRuntimeConfig:
    enabled: bool
    host: str
    port: int
    username: str
    password: str
    from_email: str
    use_tls: bool
    source: str


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _fernet() -> Fernet:
    secret = str(os.getenv("AUTH_SECRET_KEY", "") or "").strip()
    if not secret:
        raise RuntimeError("AUTH_SECRET_KEY is required to protect SMTP credentials.")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "Stored SMTP credentials cannot be decrypted with the current AUTH_SECRET_KEY."
        ) from exc


def get_application_settings(db: Session) -> ApplicationSettingsRecord | None:
    return db.get(ApplicationSettingsRecord, 1)


def get_or_create_application_settings(db: Session) -> ApplicationSettingsRecord:
    settings = get_application_settings(db)
    if settings is None:
        settings = ApplicationSettingsRecord(id=1)
        db.add(settings)
        db.flush()
    return settings


def _environment_smtp_config() -> SmtpRuntimeConfig:
    host = str(os.getenv("SMTP_HOST", "") or "").strip()
    username = str(os.getenv("SMTP_USERNAME", "") or "").strip()
    password = str(os.getenv("SMTP_PASSWORD", "") or "")
    from_email = str(os.getenv("SMTP_FROM_EMAIL", username) or "").strip()
    port = int(str(os.getenv("SMTP_PORT", "587") or "587"))
    return SmtpRuntimeConfig(
        enabled=bool(host and from_email),
        host=host,
        port=port,
        username=username,
        password=password,
        from_email=from_email,
        use_tls=_as_bool(os.getenv("SMTP_USE_TLS"), True),
        source="environment" if host or from_email else "unconfigured",
    )


def get_smtp_runtime_config() -> SmtpRuntimeConfig:
    with SessionLocal() as db:
        settings = get_application_settings(db)
        if settings is None:
            return _environment_smtp_config()

        return SmtpRuntimeConfig(
            enabled=settings.smtp_enabled,
            host=settings.smtp_host.strip(),
            port=settings.smtp_port,
            username=settings.smtp_username.strip(),
            password=decrypt_secret(settings.smtp_password_encrypted),
            from_email=settings.smtp_from_email.strip(),
            use_tls=settings.smtp_use_tls,
            source="database",
        )


def smtp_settings_response(db: Session) -> dict:
    settings = get_application_settings(db)
    if settings is None:
        config = _environment_smtp_config()
        return {
            "enabled": config.enabled,
            "host": config.host,
            "port": config.port,
            "username": config.username,
            "fromEmail": config.from_email,
            "useTls": config.use_tls,
            "passwordConfigured": bool(config.password),
            "source": config.source,
        }

    return {
        "enabled": settings.smtp_enabled,
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "username": settings.smtp_username,
        "fromEmail": settings.smtp_from_email,
        "useTls": settings.smtp_use_tls,
        "passwordConfigured": bool(settings.smtp_password_encrypted),
        "source": "database",
    }


def update_smtp_settings(
    db: Session,
    *,
    enabled: bool,
    host: str,
    port: int,
    username: str,
    password: str | None,
    from_email: str,
    use_tls: bool,
    clear_password: bool = False,
) -> ApplicationSettingsRecord:
    host = host.strip()
    username = username.strip()
    from_email = from_email.strip()

    if port < 1 or port > 65535:
        raise ValueError("SMTP port must be between 1 and 65535.")
    if enabled and not host:
        raise ValueError("SMTP host is required when SMTP is enabled.")
    if enabled and not from_email:
        raise ValueError("From email is required when SMTP is enabled.")

    settings = get_or_create_application_settings(db)
    settings.smtp_enabled = enabled
    settings.smtp_host = host
    settings.smtp_port = port
    settings.smtp_username = username
    settings.smtp_from_email = from_email
    settings.smtp_use_tls = use_tls

    if clear_password:
        settings.smtp_password_encrypted = None
    elif password is not None and password != "":
        settings.smtp_password_encrypted = encrypt_secret(password)

    if not username:
        settings.smtp_password_encrypted = None

    db.commit()
    db.refresh(settings)
    return settings


def branding_response(db: Session) -> dict:
    settings = get_application_settings(db)
    custom_logo = bool(settings and settings.logo_data and settings.logo_mime_type)
    return {
        "customLogo": custom_logo,
        "filename": settings.logo_filename if custom_logo and settings else None,
        "updatedAt": settings.updated_at.isoformat() if settings and settings.updated_at else None,
    }


def save_logo(
    db: Session,
    *,
    filename: str,
    mime_type: str,
    data: bytes,
) -> ApplicationSettingsRecord:
    settings = get_or_create_application_settings(db)
    settings.logo_filename = filename[:255]
    settings.logo_mime_type = mime_type
    settings.logo_data = data
    db.commit()
    db.refresh(settings)
    return settings


def clear_logo(db: Session) -> ApplicationSettingsRecord:
    settings = get_or_create_application_settings(db)
    settings.logo_filename = None
    settings.logo_mime_type = None
    settings.logo_data = None
    db.commit()
    db.refresh(settings)
    return settings
