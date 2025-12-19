#!/usr/bin/env python3
"""Run scrape job immediately (manual trigger)."""

import asyncio

from app.core.database import get_db_session
from app.core.logging import get_logger, setup_logging
from app.demand.scraper.orchestrator import run_scrape

logger = get_logger(__name__)


async def main() -> None:
    """Execute scrape job immediately."""
    setup_logging("INFO")

    logger.info("script.manual_scrape_started")
    print("\n🚀 Starting manual scrape...\n")

    try:
        async with get_db_session() as db:
            result = await run_scrape(db, triggered_by="manual_script")
            await db.commit()  # CRITICAL: Commit the transaction

            print("\n✅ Scrape completed successfully!")
            print(f"   Status: {result.status}")
            print(f"   Run ID: {result.run_id}")
            print(f"   Roles found: {result.roles_found}")
            print(f"   New roles: {result.new_roles}")
            print(f"   Updated roles: {result.updated_roles}")
            print(f"   Qualified roles: {result.qualified_roles}")
            print(f"   Duration: {result.duration_seconds}s")

            if result.errors:
                print(f"   ⚠️ Errors: {len(result.errors)}")
                for error in result.errors[:3]:  # Show first 3 errors
                    print(f"      - {error}")

            logger.info(
                "script.manual_scrape_completed",
                run_id=str(result.run_id),
                status=result.status,
                roles_found=result.roles_found,
            )

    except Exception as e:
        logger.error("script.manual_scrape_failed", error=str(e), exc_info=True)
        print(f"\n❌ Scrape failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
