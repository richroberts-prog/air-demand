"""Email service for sending digest emails via Mailgun HTTP API."""

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_digest_email(subject: str, html_body: str, text_body: str) -> bool:
    """Send a digest email via Mailgun HTTP API.

    Args:
        subject: Email subject line.
        html_body: HTML version of the email body.
        text_body: Plain text version of the email body.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    settings = get_settings()

    # Check if Mailgun is configured
    if not settings.mailgun_api_key or not settings.mailgun_domain or not settings.digest_recipient:
        logger.warning(
            "jobs.email.not_configured",
            mailgun_api_key_set=bool(settings.mailgun_api_key),
            mailgun_domain_set=bool(settings.mailgun_domain),
            recipient_set=bool(settings.digest_recipient),
        )
        return False

    try:
        logger.info(
            "jobs.email.send_started",
            recipient=settings.digest_recipient,
            subject=subject,
            provider="mailgun",
        )

        # Prepare Mailgun API request
        url = f"https://api.mailgun.net/v3/{settings.mailgun_domain}/messages"
        auth = ("api", settings.mailgun_api_key)
        data = {
            "from": f"AI Recruiter <mailgun@{settings.mailgun_domain}>",
            "to": settings.digest_recipient,
            "subject": subject,
            "text": text_body,
            "html": html_body,
        }

        # Send via Mailgun HTTP API
        response = httpx.post(url, auth=auth, data=data, timeout=30.0)
        response.raise_for_status()

        logger.info(
            "jobs.email.send_completed",
            recipient=settings.digest_recipient,
            subject=subject,
            provider="mailgun",
            message_id=response.json().get("id"),
        )
        return True

    except httpx.HTTPStatusError as e:
        logger.error(
            "jobs.email.http_error",
            status_code=e.response.status_code,
            error=str(e),
            response_text=e.response.text,
            exc_info=True,
        )
        return False
    except httpx.RequestError as e:
        logger.error(
            "jobs.email.request_failed",
            error=str(e),
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            "jobs.email.unexpected_error",
            error=str(e),
            exc_info=True,
        )
        return False
