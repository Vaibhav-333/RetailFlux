"""Resend email client — async wrapper with graceful no-op when key is absent."""
import asyncio
import logging

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success, False if skipped/failed."""
    from app.core.config import settings

    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured — skipping email to %s", to)
        return False

    try:
        import resend  # lazy import: only available when key is configured
        resend.api_key = settings.RESEND_API_KEY
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.EMAIL_FROM,
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        logger.info("Email sent to %s — %s", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Resend failed for %s: %s", to, exc)
        return False
