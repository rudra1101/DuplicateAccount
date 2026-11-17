from __future__ import annotations

from datetime import UTC, datetime, timedelta
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.db_models.integration import IntegrationRecord
from app.db_models.source_account import SourceAccountRecord
from app.services.account_dormancy_service import (
    DormancyConfig,
    dormancy_mappings,
    inactive_days,
    is_dormant,
)
from app.services.email_service import send_email


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def automatic_reminder_due(
    account: SourceAccountRecord,
    config: DormancyConfig,
    *,
    now: datetime | None = None,
) -> bool:
    if not config.automatic_reminders:
        return False
    if not account.email:
        return False
    if account.dormancy_ticket_id:
        return False
    if not is_dormant(account, config, now=now):
        return False

    if account.last_dormancy_reminder_at is None:
        return True

    reference = _as_utc(now or datetime.now(UTC))
    last_sent = _as_utc(account.last_dormancy_reminder_at)
    return reference - last_sent >= timedelta(days=config.reminder_interval_days)


def send_dormancy_reminder_for_account(
    db: Session,
    *,
    account: SourceAccountRecord,
    config: DormancyConfig,
    requested_by: str | None = None,
) -> dict:
    if not is_dormant(account, config):
        raise ValueError(
            "The account is no longer dormant under the current application threshold."
        )
    if not account.email:
        raise ValueError("The dormant account does not have an email address.")

    days = inactive_days(account.last_login_at)
    if days is None:
        raise ValueError("The account has no normalized last-login timestamp.")

    account_name = account.display_name or account.username or account.native_identity
    subject = f"Action required: inactive {account.application} account"
    text_body = (
        f"Hello {account_name},\n\n"
        f"Your {account.application} account has not recorded a login for {days} days. "
        f"The configured inactivity threshold is {config.threshold_days} days.\n\n"
        "If you still require this account, please sign in or contact the support team. "
        "The account may otherwise be disabled according to the organization's access policy.\n\n"
        "This is an automated IdentityAI account-governance reminder."
    )
    safe_account_name = escape(account_name)
    safe_application = escape(account.application)
    html_body = (
        f"<p>Hello {safe_account_name},</p>"
        f"<p>Your <strong>{safe_application}</strong> account has not recorded a login "
        f"for <strong>{days} days</strong>. The configured inactivity threshold is "
        f"<strong>{config.threshold_days} days</strong>.</p>"
        "<p>If you still require this account, please sign in or contact the support team. "
        "The account may otherwise be disabled according to the organization's access policy.</p>"
        "<p>This is an automated IdentityAI account-governance reminder.</p>"
    )

    send_email(
        recipients=[account.email],
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )

    sent_at = datetime.now(UTC)
    account.last_dormancy_reminder_at = sent_at
    account.updated_at = sent_at
    db.commit()
    db.refresh(account)

    return {
        "accountId": account.id,
        "recipient": account.email,
        "sentAt": account.last_dormancy_reminder_at.isoformat(),
        "inactiveDays": days,
        "thresholdDays": config.threshold_days,
        "requestedBy": (requested_by or "").strip() or None,
    }


def process_automatic_dormancy_reminders() -> dict[str, int]:
    db = SessionLocal()
    summary = {
        "integrations": 0,
        "eligible": 0,
        "sent": 0,
        "skipped": 0,
        "failed": 0,
    }

    try:
        integrations = list(
            db.scalars(
                select(IntegrationRecord)
                .where(IntegrationRecord.enabled.is_(True))
                .order_by(IntegrationRecord.id.asc())
            ).all()
        )
        reference = datetime.now(UTC)

        for integration in integrations:
            mappings = dormancy_mappings(integration.configuration)
            enabled_mappings = {
                name: config
                for name, config in mappings.items()
                if config.automatic_reminders
            }
            if not enabled_mappings:
                continue

            summary["integrations"] += 1
            accounts = list(
                db.scalars(
                    select(SourceAccountRecord).where(
                        SourceAccountRecord.integration_id == integration.id,
                        SourceAccountRecord.active.is_(True),
                        SourceAccountRecord.deleted.is_(False),
                        SourceAccountRecord.last_login_at.is_not(None),
                    )
                ).all()
            )

            for account in accounts:
                config = enabled_mappings.get(account.application.strip().casefold())
                if config is None:
                    continue

                if not automatic_reminder_due(account, config, now=reference):
                    summary["skipped"] += 1
                    continue

                summary["eligible"] += 1
                try:
                    send_dormancy_reminder_for_account(
                        db,
                        account=account,
                        config=config,
                        requested_by="SYSTEM",
                    )
                    summary["sent"] += 1
                except Exception as exc:
                    db.rollback()
                    summary["failed"] += 1
                    print(
                        "Automatic dormancy reminder failed: "
                        f"integration={integration.id}, account={account.id}, error={exc}"
                    )

        return summary
    finally:
        db.close()
