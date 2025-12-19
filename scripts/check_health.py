#!/usr/bin/env python3
"""Quick health check - shows last scrape and digest times."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import get_db_session
from app.demand.models import RoleScrapeRun, UserSettings


async def check() -> None:
    """Check scheduler health by showing recent activity."""
    async with get_db_session() as db:
        # Last scrape
        stmt = select(RoleScrapeRun).order_by(RoleScrapeRun.started_at.desc()).limit(1)
        result = await db.execute(stmt)
        last_scrape = result.scalar_one_or_none()

        # Last digest
        stmt = select(UserSettings).where(UserSettings.id == 1)
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()

        now = datetime.now(UTC)

        print("\n📊 Scheduler Health Check")
        print("=" * 50)

        if last_scrape:
            # Ensure timezone-aware comparison
            started_at = (
                last_scrape.started_at.replace(tzinfo=UTC)
                if last_scrape.started_at.tzinfo is None
                else last_scrape.started_at
            )
            age = (now - started_at).total_seconds() / 3600
            status_emoji = "✓" if last_scrape.status == "completed" else "⚠"
            print(f"{status_emoji} Last scrape: {age:.1f}h ago ({last_scrape.status})")
            print(
                f"  - Roles: {last_scrape.roles_found} found, {last_scrape.qualified_roles} qualified"
            )
            print(f"  - Duration: {last_scrape.duration_seconds}s")
        else:
            print("✗ No scrapes found")

        if settings and settings.last_digest_sent_at:
            # Ensure timezone-aware comparison
            digest_at = (
                settings.last_digest_sent_at.replace(tzinfo=UTC)
                if settings.last_digest_sent_at.tzinfo is None
                else settings.last_digest_sent_at
            )
            age = (now - digest_at).total_seconds() / 3600
            print(f"✓ Last digest: {age:.1f}h ago")
        else:
            print("✗ No digest sent")

        print("=" * 50)
        print()


if __name__ == "__main__":
    asyncio.run(check())
