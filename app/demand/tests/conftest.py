"""Pytest fixtures for jobs tests.

These fixtures use transaction rollback for test isolation, ensuring
production data is never modified.

Integration tests automatically sync from production if local database is stale
(controlled by AUTO_SYNC_DEMAND_DB environment variable, default: true).
"""

import os
import subprocess
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.database import Base


def pytest_sessionstart(session: pytest.Session) -> None:
    """Hook that runs once before all tests.

    Auto-syncs demand database from production if:
    - Any integration tests are selected
    - Local database is stale (>12 hours old)
    - AUTO_SYNC_DEMAND_DB=true (default)

    Set AUTO_SYNC_DEMAND_DB=false to disable:
        AUTO_SYNC_DEMAND_DB=false pytest app/jobs/tests/ -v -m integration
    """
    # Check if auto-sync is enabled (default: true)
    auto_sync = os.getenv("AUTO_SYNC_DEMAND_DB", "true").lower() in ("true", "1", "yes")
    if not auto_sync:
        return

    # Check if integration tests are in the run
    has_integration = any(item.get_closest_marker("integration") for item in session.items)

    if not has_integration:
        return

    # Check staleness and sync if needed
    print("\n🔄 Checking demand database freshness...")

    staleness_check = subprocess.run(
        ["./scripts/check_demand_db_staleness.sh", "--quiet", "--max-age-hours", "12"],
        capture_output=True,
    )

    if staleness_check.returncode == 0:
        print("✓ Local database is fresh\n")
        return

    if staleness_check.returncode == 2:
        print("⚠️  Cannot determine staleness, skipping auto-sync")
        print("   Run manually if needed: ./scripts/sync_demand_db_simple.sh\n")
        return

    # Database is stale, auto-sync
    print("🔄 Local database is stale, auto-syncing from production...")
    print("   (Set AUTO_SYNC_DEMAND_DB=false to disable)\n")

    sync_result = subprocess.run(
        ["./scripts/sync_demand_db_simple.sh"],
        capture_output=False,  # Show output
    )

    if sync_result.returncode != 0:
        print("\n❌ Auto-sync failed, continuing with stale data")
        print("   Tests may fail due to outdated data\n")
    else:
        print("\n✓ Auto-sync complete\n")


@pytest.fixture(scope="function")
async def test_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create fresh database engine for each test."""
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Database session with transaction rollback for test isolation.

    Uses a nested transaction pattern where the test runs within an
    outer transaction that is rolled back after completion. This ensures
    no test data persists to the actual database.
    """
    # Create tables if they don't exist (safe - only adds missing)
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_db_engine.connect() as conn:
        # Begin outer transaction
        await conn.begin()

        # Create session bound to this connection
        async_session = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )

        async with async_session() as session:
            yield session

        # Rollback outer transaction - nothing persists
        await conn.rollback()
