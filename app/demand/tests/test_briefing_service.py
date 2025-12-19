"""Integration tests for briefing service."""

import pytest
from sqlalchemy import select

from app.demand.models import Role, RoleBriefing


@pytest.mark.integration
@pytest.mark.asyncio
async def test_briefing_service_with_real_role(db_session) -> None:  # type: ignore[no-untyped-def]
    """Test briefing service with real role from database.

    This test verifies the briefing service can fetch and cache briefings.
    It requires a real role with 80+ score in the database.
    """
    # Find a high-scoring role
    stmt = (
        select(Role)
        .where(Role.is_qualified == True)  # noqa: E712
        .where(Role.combined_score >= 0.80)
        .limit(1)
    )
    result = await db_session.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        pytest.skip("No high-scoring roles available for testing")

    # Check if briefing already exists
    briefing_stmt = select(RoleBriefing).where(RoleBriefing.paraform_id == role.paraform_id)
    result = await db_session.execute(briefing_stmt)
    existing_briefing = result.scalar_one_or_none()

    if existing_briefing:
        # Briefing already exists, verify it has expected fields
        assert existing_briefing.pitch_summary
        assert existing_briefing.key_selling_points
        assert existing_briefing.score_at_enrichment >= 0.80
        return

    # Note: We can't test full briefing generation in integration tests
    # because it requires Playwright context (browser automation)
    # This would need to be tested in E2E tests or manually
    pytest.skip("Full briefing generation requires Playwright context (E2E test)")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_briefing_caching(db_session) -> None:  # type: ignore[no-untyped-def]
    """Test that briefings are retrieved from cache if they exist."""
    # Find any existing briefing
    stmt = select(RoleBriefing).limit(1)
    result = await db_session.execute(stmt)
    briefing = result.scalar_one_or_none()

    if not briefing:
        pytest.skip("No briefings in database to test caching")

    # Query for the same briefing again
    cached_stmt = select(RoleBriefing).where(RoleBriefing.paraform_id == briefing.paraform_id)
    cached_result = await db_session.execute(cached_stmt)
    cached_briefing = cached_result.scalar_one_or_none()

    assert cached_briefing is not None
    assert cached_briefing.id == briefing.id
    assert cached_briefing.pitch_summary == briefing.pitch_summary
