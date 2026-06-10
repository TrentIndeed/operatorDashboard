"""
SMTP email sender — simple Gmail App Password or any SMTP service.

Bypasses OAuth entirely. Works with:
- Gmail (use App Password from myaccount.google.com/apppasswords)
- Fastmail, Postmark, Mailgun, etc. (use their SMTP credentials)
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
# Strip whitespace from Gmail app passwords (they're typically shown as "xxxx xxxx xxxx xxxx")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").replace(" ", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
DEFAULT_TO = os.environ.get("SMTP_TO", SMTP_USER)


def send_email(
    subject: str,
    html: str,
    text: str = "",
    to: str = "",
) -> bool:
    """Send an HTML email with optional plain-text fallback via SMTP."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[Email] SMTP_USER/SMTP_PASSWORD not configured, skipping send")
        return False

    recipient = to or DEFAULT_TO
    if not recipient:
        print("[Email] No recipient configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = recipient

    if text:
        msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[Email] Sent to {recipient}: {subject}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[Email] SMTP auth failed: {e}")
        return False
    except Exception as e:
        print(f"[Email] Send failed: {e}")
        return False
