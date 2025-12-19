"""Slack webhook integration for notifications.

Sends formatted messages to Slack via incoming webhooks.
Used for OpenRouter model monitoring weekly digests.
"""

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_slack_message(text: str, blocks: list[dict[str, Any]] | None = None) -> bool:
    """Send a message to Slack via webhook.

    Args:
        text: Plain text fallback message.
        blocks: Optional Block Kit formatted blocks for rich formatting.

    Returns:
        True if message sent successfully, False otherwise.

    Example:
        success = await send_slack_message(
            text="Model update detected",
            blocks=[{
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Model Update*\nGemini 3 Flash now available"}
            }]
        )
    """
    settings = get_settings()

    if not settings.slack_webhook_url:
        logger.warning("slack.webhook_not_configured", reason="SLACK_WEBHOOK_URL not set")
        return False

    payload: dict[str, Any] = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.slack_webhook_url,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()

            logger.info("slack.message_sent", text_preview=text[:100])
            return True

        except httpx.HTTPError as e:
            logger.error(
                "slack.send_failed",
                exc_info=True,
                error=str(e),
            )
            return False
