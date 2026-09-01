from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ScheduledReportConfigRecord(Base):
    __tablename__ = "scheduled_report_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="MONTHLY")
    include_admins: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recipient_emails: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    selected_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    email_template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="Asia/Kolkata")
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ScheduledReportRunRecord(Base):
    __tablename__ = "scheduled_report_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_name: Mapped[str] = mapped_column(
        String(150), nullable=False, default="Executive Duplicate Risk Report"
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="GENERATED", index=True)
    test_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recipients: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    csv_content: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
