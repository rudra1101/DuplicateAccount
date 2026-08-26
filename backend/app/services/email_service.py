from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def send_email(
    *,
    recipients: list[str],
    subject: str,
    text_body: str,
    html_body: str | None = None,
    attachment_name: str | None = None,
    attachment_content: str | None = None,
) -> None:
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM_EMAIL", username).strip()
    use_tls = _as_bool(os.getenv("SMTP_USE_TLS"), True)

    if not host or not sender:
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL."
        )

    cleaned_recipients = sorted({item.strip() for item in recipients if item.strip()})
    if not cleaned_recipients:
        raise RuntimeError("No report recipients are configured.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
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

    with smtplib.SMTP(host, port, timeout=30) as server:
        if use_tls:
            server.starttls()
        if username:
            server.login(username, password)
        server.send_message(message)
