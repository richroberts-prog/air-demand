"""Tests for interview and hiring change detection."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.demand.models import Role, RoleChange, RoleScrapeRun
from app.demand.services.interview_trends import calculate_interview_trend
from app.demand.temporal import detect_changes


@pytest.mark.integration
async def test_interview_increase_detection(db_session: AsyncSession) -> None:
    """Test that INTERVIEW_INCREASE change is detected when total_interviewing increases."""
    # Create role and scrape run
    scrape_run = RoleScrapeRun(
        run_id=uuid.uuid4(),
        triggered_by="test",
        status="running",
        started_at=datetime.now(UTC),
    )
    db_session.add(scrape_run)
    await db_session.flush()

    role = Role(
        paraform_id="test-role-1",
        raw_response={"title": "Test Role", "total_interviewing": 5},
        lifecycle_status="ACTIVE",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(role)
    await db_session.flush()

    # Simulate change: interviews increased from 3 to 5
    old_data = {"title": "Test Role", "total_interviewing": 3}
    new_data = {"title": "Test Role", "total_interviewing": 5}

    changes = await detect_changes(db_session, role, old_data, new_data, scrape_run)

    # Verify INTERVIEW_INCREASE change was created
    assert len(changes) == 1
    assert changes[0].change_type == "INTERVIEW_INCREASE"
    assert changes[0].field_name == "total_interviewing"
    assert changes[0].old_value == "3"
    assert changes[0].new_value == "5"


@pytest.mark.integration
async def test_interview_decrease_detection(db_session: AsyncSession) -> None:
    """Test that INTERVIEW_DECREASE change is detected when total_interviewing decreases."""
    scrape_run = RoleScrapeRun(
        run_id=uuid.uuid4(),
        triggered_by="test",
        status="running",
        started_at=datetime.now(UTC),
    )
    db_session.add(scrape_run)
    await db_session.flush()

    role = Role(
        paraform_id="test-role-2",
        raw_response={"title": "Test Role", "total_interviewing": 2},
        lifecycle_status="ACTIVE",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(role)
    await db_session.flush()

    # Simulate change: interviews decreased from 5 to 2
    old_data = {"title": "Test Role", "total_interviewing": 5}
    new_data = {"title": "Test Role", "total_interviewing": 2}

    changes = await detect_changes(db_session, role, old_data, new_data, scrape_run)

    # Verify INTERVIEW_DECREASE change was created
    assert len(changes) == 1
    assert changes[0].change_type == "INTERVIEW_DECREASE"
    assert changes[0].field_name == "total_interviewing"
    assert changes[0].old_value == "5"
    assert changes[0].new_value == "2"


@pytest.mark.integration
async def test_hiring_increase_detection(db_session: AsyncSession) -> None:
    """Test that HIRING_INCREASE change is detected when total_hired increases."""
    scrape_run = RoleScrapeRun(
        run_id=uuid.uuid4(),
        triggered_by="test",
        status="running",
        started_at=datetime.now(UTC),
    )
    db_session.add(scrape_run)
    await db_session.flush()

    role = Role(
        paraform_id="test-role-3",
        raw_response={"title": "Test Role", "total_hired": 3},
        lifecycle_status="ACTIVE",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(role)
    await db_session.flush()

    # Simulate change: hires increased from 1 to 3
    old_data = {"title": "Test Role", "total_hired": 1}
    new_data = {"title": "Test Role", "total_hired": 3}

    changes = await detect_changes(db_session, role, old_data, new_data, scrape_run)

    # Verify HIRING_INCREASE change was created
    assert len(changes) == 1
    assert changes[0].change_type == "HIRING_INCREASE"
    assert changes[0].field_name == "total_hired"
    assert changes[0].old_value == "1"
    assert changes[0].new_value == "3"


@pytest.mark.integration
async def test_no_change_when_equal(db_session: AsyncSession) -> None:
    """Test that no change is detected when values are equal."""
    scrape_run = RoleScrapeRun(
        run_id=uuid.uuid4(),
        triggered_by="test",
        status="running",
        started_at=datetime.now(UTC),
    )
    db_session.add(scrape_run)
    await db_session.flush()

    role = Role(
        paraform_id="test-role-4",
        raw_response={"title": "Test Role", "total_interviewing": 5},
        lifecycle_status="ACTIVE",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(role)
    await db_session.flush()

    # Same values - no change
    old_data = {"title": "Test Role", "total_interviewing": 5}
    new_data = {"title": "Test Role", "total_interviewing": 5}

    changes = await detect_changes(db_session, role, old_data, new_data, scrape_run)

    # Verify no changes were created
    assert len(changes) == 0


@pytest.mark.integration
async def test_null_handling(db_session: AsyncSession) -> None:
    """Test handling of None values in interview/hiring fields."""
    scrape_run = RoleScrapeRun(
        run_id=uuid.uuid4(),
        triggered_by="test",
        status="running",
        started_at=datetime.now(UTC),
    )
    db_session.add(scrape_run)
    await db_session.flush()

    role = Role(
        paraform_id="test-role-5",
        raw_response={"title": "Test Role", "total_interviewing": 5},
        lifecycle_status="ACTIVE",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(role)
    await db_session.flush()

    # Test None -> value transition
    old_data = {"title": "Test Role", "total_interviewing": None}
    new_data = {"title": "Test Role", "total_interviewing": 5}

    changes = await detect_changes(db_session, role, old_data, new_data, scrape_run)

    # Verify change was detected (None -> 5 is a change)
    assert len(changes) == 1
    assert changes[0].change_type == "INTERVIEW_INCREASE"

    # Test value -> None transition
    old_data2 = {"title": "Test Role", "total_interviewing": 5}
    new_data2 = {"title": "Test Role", "total_interviewing": None}

    changes2 = await detect_changes(db_session, role, old_data2, new_data2, scrape_run)

    # Verify change was detected (5 -> None is a change)
    assert len(changes2) == 1
    assert changes2[0].change_type == "INTERVIEW_DECREASE"


def test_trend_calculation() -> None:
    """Test the calculate_interview_trend function logic."""
    # Create a mock role
    role = Role(
        id=1,
        paraform_id="test-role-trend",
        raw_response={"title": "Test Role"},
        lifecycle_status="ACTIVE",
    )

    # Test: Surging (INTERVIEW_INCREASE)
    changes_surging = {
        1: [
            RoleChange(
                id=1,
                role_id=1,
                scrape_run_id=1,
                change_type="INTERVIEW_INCREASE",
                field_name="total_interviewing",
                old_value="3",
                new_value="8",
                detected_at=datetime.now(UTC),
            )
        ]
    }
    assert calculate_interview_trend(role, changes_surging) == "surging"

    # Test: Stalled (INTERVIEW_DECREASE to 0)
    changes_stalled = {
        1: [
            RoleChange(
                id=2,
                role_id=1,
                scrape_run_id=1,
                change_type="INTERVIEW_DECREASE",
                field_name="total_interviewing",
                old_value="5",
                new_value="0",
                detected_at=datetime.now(UTC),
            )
        ]
    }
    assert calculate_interview_trend(role, changes_stalled) == "stalled"

    # Test: Hired (HIRING_INCREASE takes priority)
    changes_hired = {
        1: [
            RoleChange(
                id=3,
                role_id=1,
                scrape_run_id=1,
                change_type="HIRING_INCREASE",
                field_name="total_hired",
                old_value="1",
                new_value="2",
                detected_at=datetime.now(UTC),
            ),
            RoleChange(
                id=4,
                role_id=1,
                scrape_run_id=1,
                change_type="INTERVIEW_INCREASE",
                field_name="total_interviewing",
                old_value="3",
                new_value="5",
                detected_at=datetime.now(UTC),
            ),
        ]
    }
    assert calculate_interview_trend(role, changes_hired) == "hired"

    # Test: No trend (no changes)
    changes_none: dict[int, list[RoleChange]] = {}
    assert calculate_interview_trend(role, changes_none) is None

    # Test: No trend (decrease but not to 0)
    changes_decrease_not_zero = {
        1: [
            RoleChange(
                id=5,
                role_id=1,
                scrape_run_id=1,
                change_type="INTERVIEW_DECREASE",
                field_name="total_interviewing",
                old_value="5",
                new_value="3",
                detected_at=datetime.now(UTC),
            )
        ]
    }
    assert calculate_interview_trend(role, changes_decrease_not_zero) is None
