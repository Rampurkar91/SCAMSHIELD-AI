"""Transactional email with STARTTLS; no token/recipient logging."""

import os
import smtplib
import ssl
from email.message import EmailMessage
from fastapi import HTTPException


def send_email(recipient: str, subject: str, body: str):
    sender = os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_FROM")
    if not os.getenv("SMTP_HOST") or not sender:
        raise HTTPException(
            503, "Email delivery is not configured. Contact the administrator."
        )
    if os.getenv("SMTP_USERNAME") and not os.getenv("SMTP_PASSWORD"):
        raise HTTPException(503, "SMTP authentication is not fully configured.")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(
            os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=10
        ) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if os.getenv("SMTP_USERNAME"):
                smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError):
        raise HTTPException(503, "Email delivery is unavailable. Please try later.")
