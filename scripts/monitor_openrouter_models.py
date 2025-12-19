"""Monitor OpenRouter models for changes and send weekly digest.

This script:
1. Fetches all models from OpenRouter API
2. Compares with database state
3. Detects changes (new models, price changes)
4. Updates database with new state
5. Logs changes to audit table
6. Sends Slack digest of changes

Usage:
    # Run manually
    uv run python scripts/monitor_openrouter_models.py

    # Scheduled via APScheduler (weekly)
    See app/scheduler.py
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.logging import get_logger
from app.core.model_monitoring import build_slack_digest
from app.core.openrouter import (
    fetch_all_models,
    fetch_usage_stats,
    filter_models_by_provider,
    parse_model_data,
)
from app.core.slack import send_slack_message
from app.shared.models import OpenRouterModel, OpenRouterModelChange

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Get supply database URL from environment
supply_db_url = os.getenv("SUPPLY_DATABASE_URL")
if not supply_db_url:
    raise ValueError("SUPPLY_DATABASE_URL environment variable not set")

# Create engine for supply database
supply_engine = create_async_engine(supply_db_url, pool_pre_ping=True)
SupplySessionLocal = async_sessionmaker(
    supply_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def detect_changes(
    db: AsyncSession,
    providers: list[str] = ["google", "anthropic"],
) -> list[OpenRouterModelChange]:
    """Detect changes between OpenRouter API and database state.

    Args:
        db: Database session.
        providers: List of provider prefixes to track (default: Google and Anthropic).

    Returns:
        List of detected changes (not yet committed to DB).
    """
    logger.info("monitor.detection_started", providers=providers)

    # Fetch all models from OpenRouter
    all_models = await fetch_all_models()

    # Filter to our providers
    api_models = filter_models_by_provider(all_models, providers)

    # Get all existing models from DB
    result = await db.execute(select(OpenRouterModel))
    db_models = {model.model_id: model for model in result.scalars().all()}

    changes = []
    now = datetime.now(UTC)

    # Check each API model
    for api_model_raw in api_models:
        api_model = parse_model_data(api_model_raw)
        model_id = api_model["model_id"]

        if model_id not in db_models:
            # New model detected
            change = OpenRouterModelChange(
                model_id=model_id,
                change_type="new_model",
                field_changed=None,
                old_value=None,
                new_value=f"{api_model['model_name']} - ${api_model['input_price']}/{api_model['output_price']}",
                detected_at=now,
                notified=False,
            )
            changes.append(change)

            # Create new model record
            new_model = OpenRouterModel(**api_model)
            db.add(new_model)

            logger.info(
                "monitor.new_model_detected",
                model_id=model_id,
                model_name=api_model["model_name"],
            )
        else:
            # Check for price changes
            db_model = db_models[model_id]

            # Input price change
            if abs(float(db_model.input_price) - api_model["input_price"]) > 0.001:
                change_type = (
                    "price_decrease"
                    if api_model["input_price"] < float(db_model.input_price)
                    else "price_increase"
                )
                change = OpenRouterModelChange(
                    model_id=model_id,
                    change_type=change_type,
                    field_changed="input_price",
                    old_value=str(db_model.input_price),
                    new_value=str(api_model["input_price"]),
                    detected_at=now,
                    notified=False,
                )
                changes.append(change)

                # Update model
                db_model.input_price = Decimal(str(api_model["input_price"]))

                logger.info(
                    "monitor.price_change_detected",
                    model_id=model_id,
                    field="input_price",
                    old_value=change.old_value,
                    new_value=change.new_value,
                    change_type=change_type,
                )

            # Output price change
            if abs(float(db_model.output_price) - api_model["output_price"]) > 0.001:
                change_type = (
                    "price_decrease"
                    if api_model["output_price"] < float(db_model.output_price)
                    else "price_increase"
                )
                change = OpenRouterModelChange(
                    model_id=model_id,
                    change_type=change_type,
                    field_changed="output_price",
                    old_value=str(db_model.output_price),
                    new_value=str(api_model["output_price"]),
                    detected_at=now,
                    notified=False,
                )
                changes.append(change)

                # Update model
                db_model.output_price = Decimal(str(api_model["output_price"]))

                logger.info(
                    "monitor.price_change_detected",
                    model_id=model_id,
                    field="output_price",
                    old_value=change.old_value,
                    new_value=change.new_value,
                    change_type=change_type,
                )

    # Add all changes to session
    for change in changes:
        db.add(change)

    await db.commit()

    logger.info(
        "monitor.detection_completed",
        changes_detected=len(changes),
    )

    return changes


async def main() -> None:
    """Main entry point for monitoring script."""
    logger.info("monitor.started")

    async with SupplySessionLocal() as db:
        try:
            # Detect changes and update DB
            changes = await detect_changes(db)

            # Fetch usage stats (optional)
            usage_stats = await fetch_usage_stats()

            if changes:
                logger.info(
                    "monitor.changes_summary",
                    total_changes=len(changes),
                    new_models=sum(1 for c in changes if c.change_type == "new_model"),
                    price_changes=sum(
                        1 for c in changes if c.change_type in ["price_increase", "price_decrease"]
                    ),
                )

                # Build and send Slack digest
                digest = build_slack_digest(changes, usage_stats)
                success = await send_slack_message(**digest)

                if success:
                    # Mark changes as notified
                    for change in changes:
                        change.notified = True
                    await db.commit()

                    logger.info("monitor.notification_sent")
                else:
                    logger.warning("monitor.notification_failed")
            else:
                logger.info("monitor.no_changes_detected")

        except Exception as e:
            logger.error(
                "monitor.failed",
                exc_info=True,
                error=str(e),
            )
            raise

    logger.info("monitor.completed")


if __name__ == "__main__":
    asyncio.run(main())
