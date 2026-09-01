from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.services.settings_service import get_smtp_runtime_config


def send_email(
    *,
    recipients: list[str],
    subject: str,
    text_body: str,
    html_body: str | None = None,
    attachment_name: str | None = None,
    attachment_content: str | None = None,
) -> None:
    config = get_smtp_runtime_config()

    if not config.enabled:
        raise RuntimeError("SMTP is disabled or not configured.")
    if not config.host or not config.from_email:
        raise RuntimeError("SMTP host and from email are required.")

    cleaned_recipients = sorted({item.strip() for item in recipients if item.strip()})
    if not cleaned_recipients:
        raise RuntimeError("No report recipients are configured.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.from_email
    message["To"] = ", ".join(cleaned_recipients)
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    if attachment_name and attachment_content is not None:
        message.add_attachment(
            attachment_content.encode("utf-8-sig"),
            maintype="text",
            subtype="csv",
            filename=attachment_name,
        )

    with smtplib.SMTP(config.host, config.port, timeout=30) as server:
        if config.use_tls:
            server.starttls()
        if config.username:
            server.login(config.username, config.password)
        server.send_message(message)
