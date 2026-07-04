"""Production SMTP sender with retry logic, rate limiting, and comprehensive logging.

In DEMO_MODE or on connectivity failure — writes .eml to disk as fallback.
"""
from __future__ import annotations

import logging
import os
import time
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from ..settings import settings

logger = logging.getLogger(__name__)

DUMP_DIR = Path("data/sent_emails")

# Simple in-memory rate limiter: max emails per minute per recipient
_RATE_LIMIT_PER_MIN = 10
_rate_tracker: dict[str, list[float]] = {}


def _check_rate_limit(recipient: str) -> bool:
    """Return True if sending is allowed."""
    now = time.time()
    window = _rate_tracker.setdefault(recipient, [])
    _rate_tracker[recipient] = [t for t in window if now - t < 60]
    if len(_rate_tracker[recipient]) >= _RATE_LIMIT_PER_MIN:
        return False
    _rate_tracker[recipient].append(now)
    return True


async def send_rfq_email(
    supplier_email: str | None,
    subject: str,
    body: str,
    reply_to: str,
    attachments: list[tuple[str, bytes]] | None = None,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> str:
    """Send an RFQ email via SMTP with retries. Falls back to .eml dump on failure.

    Returns the generated Message-ID.
    """
    if not supplier_email:
        supplier_email = f"noreply@{settings.demo_email_domain}"

    # Rate limit check
    if not _check_rate_limit(supplier_email):
        logger.warning(
            "email_rate_limited",
            extra={"recipient": supplier_email, "limit": _RATE_LIMIT_PER_MIN},
        )
        raise RuntimeError(f"Rate limit exceeded for {supplier_email}")

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = supplier_email
    msg["Reply-To"] = reply_to
    msg["Subject"] = subject
    msg_id = make_msgid(domain=settings.demo_email_domain).strip("<>")
    msg["Message-ID"] = f"<{msg_id}>"
    msg.set_content(body)
    if attachments:
        for fname, content in attachments:
            msg.add_attachment(
                content,
                maintype="application",
                subtype="octet-stream",
                filename=fname,
            )

    sent_via_smtp = False
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            import aiosmtplib

            kwargs: dict = {
                "hostname": settings.smtp_host,
                "port": settings.smtp_port,
                "timeout": 15,
            }
            if settings.smtp_use_tls:
                kwargs["start_tls"] = True
            if settings.smtp_user:
                kwargs["username"] = settings.smtp_user
            if settings.smtp_password.get_secret_value():
                kwargs["password"] = settings.smtp_password.get_secret_value()

            await aiosmtplib.send(msg, **kwargs)
            sent_via_smtp = True
            logger.info(
                "email_sent",
                extra={
                    "message_id": msg_id,
                    "recipient": supplier_email,
                    "attempt": attempt,
                },
            )
            break
        except ImportError:
            logger.warning("aiosmtplib not installed, falling back to .eml dump")
            break
        except Exception as e:
            last_error = e
            logger.warning(
                "email_send_attempt_failed",
                extra={
                    "message_id": msg_id,
                    "recipient": supplier_email,
                    "attempt": attempt,
                    "error": str(e),
                },
            )
            if attempt < max_retries:
                import asyncio

                await asyncio.sleep(retry_delay * attempt)

    if not sent_via_smtp:
        DUMP_DIR.mkdir(parents=True, exist_ok=True)
        path = DUMP_DIR / f"{msg_id}.eml"
        path.write_bytes(bytes(msg))
        os.environ.setdefault("SNABAGENT_LAST_DUMP", str(path))
        logger.info(
            "email_dumped_to_disk",
            extra={
                "message_id": msg_id,
                "path": str(path),
                "last_error": str(last_error) if last_error else None,
            },
        )

    return msg_id


async def send_verification_email(email: str, token: str) -> str:
    """Send email verification link to user."""
    verify_url = f"{settings.service_public_url}/api/v1/auth/verify-email?token={token}"
    subject = "SnabAgent — подтверждение email"
    body = f"""Здравствуйте!

Для подтверждения вашего email-адреса перейдите по ссылке:

{verify_url}

Ссылка действительна 24 часа.

Если вы не регистрировались в SnabAgent — просто проигнорируйте это письмо.

---
SnabAgent — автоматизация закупок
"""
    return await send_rfq_email(
        supplier_email=email,
        subject=subject,
        body=body,
        reply_to=settings.smtp_from,
    )
