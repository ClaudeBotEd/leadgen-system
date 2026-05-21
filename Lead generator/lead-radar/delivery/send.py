"""SMTP sender (stdlib smtplib + EmailMessage).

Plain-text is the primary content; HTML is the alternative.
No tracking pixel, no attachments V0, no auto-bcc.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from .config import DeliveryConfig


def build_email_message(
    *,
    subject: str,
    preheader: str,
    from_display: str,
    from_address: str,
    to_display: str,
    to_address: str,
    body_text: str,
    body_html: str,
    case_id: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{from_display} <{from_address}>"
    msg["To"] = f"{to_display} <{to_address}>"
    msg["Reply-To"] = from_address
    msg["Subject"] = subject
    msg["X-LeadRadar-Case-ID"] = case_id
    msg["Message-ID"] = make_msgid(domain=from_address.split("@", 1)[-1])
    msg.set_content(f"{preheader}\n\n{body_text}")
    msg.add_alternative(body_html, subtype="html")
    return msg


def send_smtp(message: EmailMessage, config: DeliveryConfig) -> str:
    if config.dry_run:
        return "dry-run"
    with smtplib.SMTP(config.smtp_host, config.smtp_port) as client:
        if config.smtp_use_tls:
            client.starttls()
        client.login(config.smtp_user, config.smtp_password)
        client.send_message(message)
    return str(message["Message-ID"])
