from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any


def send_email(
    config: dict[str, Any],
    subject: str,
    html_body: str,
    markdown_path: str | None,
    logger,
) -> bool:
    delivery = config.get("delivery", {})
    if not delivery.get("email_enabled", True):
        return False

    host = delivery.get("smtp_host")
    port = int(delivery.get("smtp_port", 587) or 587)
    user = delivery.get("smtp_user")
    password = delivery.get("smtp_password")
    to_address = delivery.get("email_to")
    if not all([host, user, password, to_address]):
        logger.warning("SMTP settings are incomplete; skipping email delivery.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = user
    message["To"] = to_address
    message.set_content("你的邮件客户端不支持 HTML，请查看附件或 GitHub 仓库中的 Markdown 简报。")
    message.add_alternative(html_body, subtype="html")

    if delivery.get("attach_markdown") and markdown_path:
        path = Path(markdown_path)
        if path.exists():
            message.add_attachment(
                path.read_bytes(),
                maintype="text",
                subtype="markdown",
                filename=path.name,
            )

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
                smtp.login(user, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(message)
        return True
    except Exception as error:  # noqa: BLE001 - email failure must not fail the run.
        logger.warning("Email delivery failed: %s", error)
        return False
