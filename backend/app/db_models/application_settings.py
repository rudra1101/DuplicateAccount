from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ApplicationSettingsRecord(Base):
    __tablename__ = "application_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    smtp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    smtp_username: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    smtp_password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_from_email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    service_desk_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    service_desk_name: Mapped[str] = mapped_column(String(150), nullable=False, default="Service Desk")
    service_desk_base_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    service_desk_auth_type: Mapped[str] = mapped_column(String(20), nullable=False, default="BEARER")
    service_desk_username: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    service_desk_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_desk_create_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="/tickets")
    service_desk_status_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="/tickets/{ticket_id}")
    service_desk_ticket_id_field: Mapped[str] = mapped_column(String(255), nullable=False, default="id")
    service_desk_ticket_status_field: Mapped[str] = mapped_column(String(255), nullable=False, default="status")
    service_desk_ticket_url_field: Mapped[str] = mapped_column(String(255), nullable=False, default="url")
    service_desk_completed_statuses: Mapped[str] = mapped_column(String(500), nullable=False, default="completed,resolved,closed")
    service_desk_payload_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='{"summary":"{{summary}}","description":"{{description}}","action":"{{action}}","accountKey":"{{account_key}}","application":"{{application}}"}',
    )
    service_desk_verify_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    remediation_sla_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remediation_sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=72)
    remediation_warning_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    remediation_auto_escalate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remediation_escalation_emails: Mapped[str] = mapped_column(Text, nullable=False, default="")

    logo_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
