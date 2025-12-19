"""OpenRouter model monitoring digest formatter.

Formats detected model changes into Slack-ready digest messages.
"""

from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.shared.models import OpenRouterModelChange

logger = get_logger(__name__)


def format_price(price: float) -> str:
    """Format price for display.

    Args:
        price: Price per 1M tokens.

    Returns:
        Formatted price string (e.g., "$0.10/1M").

    Example:
        format_price(0.10) -> "$0.10/1M"
        format_price(3.50) -> "$3.50/1M"
    """
    return f"${price:.2f}/1M"


def format_change_emoji(change_type: str) -> str:
    """Get emoji for change type.

    Args:
        change_type: Type of change (new_model, price_increase, price_decrease).

    Returns:
        Emoji string.
    """
    emojis = {
        "new_model": "🆕",
        "price_increase": "📈",
        "price_decrease": "📉",
    }
    return emojis.get(change_type, "ℹ️")


def build_slack_digest(
    changes: list[OpenRouterModelChange],
    usage_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Slack Block Kit message from model changes.

    Args:
        changes: List of detected changes from database.
        usage_stats: Optional usage statistics from OpenRouter API.

    Returns:
        Dictionary with 'text' and 'blocks' for Slack webhook.

    Example:
        digest = build_slack_digest(changes)
        await send_slack_message(**digest)
    """
    if not changes:
        return {
            "text": "OpenRouter Model Monitoring - No changes this week",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "OpenRouter Model Monitoring",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ No model or pricing changes detected this week.",
                    },
                },
            ],
        }

    # Group changes by type
    new_models = [c for c in changes if c.change_type == "new_model"]
    price_increases = [c for c in changes if c.change_type == "price_increase"]
    price_decreases = [c for c in changes if c.change_type == "price_decrease"]

    # Build header
    total_changes = len(changes)
    week_str = datetime.now().strftime("%b %d, %Y")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"OpenRouter Model Monitoring - {week_str}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{total_changes} change(s) detected this week*",
            },
        },
        {"type": "divider"},
    ]

    # New models section
    if new_models:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🆕 New Models ({len(new_models)})*",
                },
            }
        )

        for change in new_models:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• `{change.model_id}`\n  {change.new_value}",
                    },
                }
            )

        blocks.append({"type": "divider"})

    # Price decreases section (good news first!)
    if price_decreases:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📉 Price Decreases ({len(price_decreases)})*",
                },
            }
        )

        for change in price_decreases:
            field_name = "Input" if change.field_changed == "input_price" else "Output"
            old_price = float(change.old_value) if change.old_value else 0
            new_price = float(change.new_value) if change.new_value else 0
            savings = ((old_price - new_price) / old_price * 100) if old_price > 0 else 0

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"• `{change.model_id}`\n"
                            f"  {field_name}: {format_price(old_price)} → {format_price(new_price)} "
                            f"(*{savings:.1f}% savings*)"
                        ),
                    },
                }
            )

        blocks.append({"type": "divider"})

    # Price increases section
    if price_increases:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📈 Price Increases ({len(price_increases)})*",
                },
            }
        )

        for change in price_increases:
            field_name = "Input" if change.field_changed == "input_price" else "Output"
            old_price = float(change.old_value) if change.old_value else 0
            new_price = float(change.new_value) if change.new_value else 0
            increase = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"• `{change.model_id}`\n"
                            f"  {field_name}: {format_price(old_price)} → {format_price(new_price)} "
                            f"(*+{increase:.1f}%*)"
                        ),
                    },
                }
            )

        blocks.append({"type": "divider"})

    # Usage stats section (optional)
    if usage_stats:
        top_models = usage_stats.get("top_models", [])[:5]
        if top_models:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📊 Top Models on OpenRouter*",
                    },
                }
            )

            for i, model in enumerate(top_models, 1):
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{i}. `{model['id']}` - {model.get('usage', 'N/A')} requests",
                        },
                    }
                )

    # Footer
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Automated monitoring via `scripts/monitor_openrouter_models.py`",
                }
            ],
        }
    )

    # Build plain text fallback
    text_parts = [f"OpenRouter Model Monitoring - {week_str}"]
    if new_models:
        text_parts.append(f"{len(new_models)} new model(s)")
    if price_decreases:
        text_parts.append(f"{len(price_decreases)} price decrease(s)")
    if price_increases:
        text_parts.append(f"{len(price_increases)} price increase(s)")

    plain_text = " | ".join(text_parts)

    logger.info(
        "digest.formatted",
        total_changes=total_changes,
        new_models=len(new_models),
        price_changes=len(price_increases) + len(price_decreases),
    )

    return {
        "text": plain_text,
        "blocks": blocks,
    }
