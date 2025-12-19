"""Unit tests for temporal tracking (snapshots and change detection).

Tests snapshot creation, change detection logic, and lifecycle transitions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.demand.temporal import (
    TRACKED_FIELDS,
    TRACKED_SET_FIELDS,
    _extract_field,  # pyright: ignore[reportPrivateUsage]
    _format_value,  # pyright: ignore[reportPrivateUsage]
    detect_changes,
)


class TestExtractField:
    """Tests for field extraction helper."""

    def test_simple_field(self) -> None:
        """Extract top-level field."""
        data = {"name": "Test", "value": 123}
        assert _extract_field(data, "name") == "Test"
        assert _extract_field(data, "value") == 123

    def test_missing_field(self) -> None:
        """Missing field returns None."""
        data = {"name": "Test"}
        assert _extract_field(data, "missing") is None

    def test_nested_field(self) -> None:
        """Extract nested field with dot notation."""
        data = {"company": {"name": "TestCo", "size": 50}}
        assert _extract_field(data, "company.name") == "TestCo"
        assert _extract_field(data, "company.size") == 50

    def test_deeply_nested_field(self) -> None:
        """Extract deeply nested field."""
        data = {"a": {"b": {"c": "deep"}}}
        assert _extract_field(data, "a.b.c") == "deep"

    def test_missing_nested_field(self) -> None:
        """Missing nested field returns None."""
        data = {"company": {"name": "TestCo"}}
        assert _extract_field(data, "company.missing") is None
        assert _extract_field(data, "missing.field") is None


class TestFormatValue:
    """Tests for value formatting helper."""

    def test_none(self) -> None:
        """None returns None."""
        assert _format_value(None) is None

    def test_string(self) -> None:
        """String returns as-is."""
        assert _format_value("test") == "test"

    def test_number(self) -> None:
        """Numbers are converted to string."""
        assert _format_value(123) == "123"
        assert _format_value(45.67) == "45.67"

    def test_list(self) -> None:
        """Lists are joined with commas."""
        assert _format_value(["a", "b", "c"]) == "a, b, c"
        assert _format_value([1, 2, 3]) == "1, 2, 3"

    def test_empty_list(self) -> None:
        """Empty list returns empty string."""
        assert _format_value([]) == ""


class TestDetectChanges:
    """Tests for change detection logic."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def mock_role(self) -> MagicMock:
        """Create mock role object."""
        role = MagicMock()
        role.id = 1
        return role

    @pytest.fixture
    def mock_scrape_run(self) -> MagicMock:
        """Create mock scrape run object."""
        run = MagicMock()
        run.id = 100
        return run

    @pytest.mark.asyncio
    async def test_no_changes_same_data(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """No changes when old and new data are identical."""
        data = {"salaryUpperBound": 200000, "percent_fee": 15.0}

        changes = await detect_changes(mock_db, mock_role, data, data, mock_scrape_run)

        assert changes == []
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_changes_first_scrape(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """No changes when old_data is None (first scrape)."""
        new_data = {"salaryUpperBound": 200000}

        changes = await detect_changes(mock_db, mock_role, None, new_data, mock_scrape_run)

        assert changes == []

    @pytest.mark.asyncio
    async def test_salary_increase_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Salary increase is detected."""
        old_data = {"salaryUpperBound": 200000}
        new_data = {"salaryUpperBound": 250000}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 1
        assert changes[0].change_type == "SALARY_INCREASE"
        assert changes[0].field_name == "salaryUpperBound"
        assert changes[0].old_value == "200000"
        assert changes[0].new_value == "250000"

    @pytest.mark.asyncio
    async def test_salary_decrease_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Salary decrease is detected."""
        old_data = {"salaryUpperBound": 250000}
        new_data = {"salaryUpperBound": 200000}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 1
        assert changes[0].change_type == "SALARY_DECREASE"

    @pytest.mark.asyncio
    async def test_fee_change_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Fee change is detected."""
        old_data = {"percent_fee": 15.0}
        new_data = {"percent_fee": 18.0}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 1
        assert changes[0].change_type == "FEE_CHANGE"
        assert changes[0].field_name == "percent_fee"

    @pytest.mark.asyncio
    async def test_headcount_change_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Hiring count change is detected."""
        old_data = {"hiring_count": 2}
        new_data = {"hiring_count": 5}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 1
        assert changes[0].change_type == "HEADCOUNT_CHANGE"

    @pytest.mark.asyncio
    async def test_competition_change_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Recruiter count change is detected."""
        old_data = {"approved_recruiters_count": 3}
        new_data = {"approved_recruiters_count": 8}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 1
        assert changes[0].change_type == "COMPETITION_CHANGE"

    @pytest.mark.asyncio
    async def test_location_change_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Location change is detected (set comparison)."""
        old_data = {"locations": ["New York", "San Francisco"]}
        new_data = {"locations": ["New York", "Remote"]}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 1
        assert changes[0].change_type == "LOCATION_CHANGE"
        assert changes[0].old_value is not None
        assert changes[0].new_value is not None
        assert "San Francisco" in changes[0].old_value
        assert "Remote" in changes[0].new_value

    @pytest.mark.asyncio
    async def test_location_reorder_no_change(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Reordering locations should not count as change."""
        old_data = {"locations": ["New York", "San Francisco"]}
        new_data = {"locations": ["San Francisco", "New York"]}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 0

    @pytest.mark.asyncio
    async def test_multiple_changes_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Multiple changes detected in same scrape."""
        old_data = {
            "salaryUpperBound": 200000,
            "percent_fee": 15.0,
            "hiring_count": 2,
        }
        new_data = {
            "salaryUpperBound": 250000,
            "percent_fee": 18.0,
            "hiring_count": 5,
        }

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 3
        change_types = {c.change_type for c in changes}
        assert "SALARY_INCREASE" in change_types
        assert "FEE_CHANGE" in change_types
        assert "HEADCOUNT_CHANGE" in change_types

    @pytest.mark.asyncio
    async def test_new_field_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """New field appearing is detected as change."""
        old_data = {"salaryUpperBound": 200000}
        new_data = {"salaryUpperBound": 200000, "percent_fee": 15.0}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 1
        assert changes[0].change_type == "FEE_CHANGE"
        assert changes[0].old_value is None
        assert changes[0].new_value == "15.0"

    @pytest.mark.asyncio
    async def test_removed_field_detected(
        self, mock_db: AsyncMock, mock_role: MagicMock, mock_scrape_run: MagicMock
    ) -> None:
        """Field removal is detected as change."""
        old_data = {"salaryUpperBound": 200000, "percent_fee": 15.0}
        new_data = {"salaryUpperBound": 200000}

        changes = await detect_changes(mock_db, mock_role, old_data, new_data, mock_scrape_run)

        assert len(changes) == 1
        assert changes[0].old_value == "15.0"
        assert changes[0].new_value is None


class TestTrackedFieldsConfig:
    """Tests for tracked fields configuration."""

    def test_tracked_fields_have_change_types(self) -> None:
        """All tracked fields should have increase/decrease types."""
        for field, (inc_type, dec_type) in TRACKED_FIELDS.items():
            assert isinstance(inc_type, str)
            assert isinstance(dec_type, str)
            assert len(inc_type) > 0
            assert len(dec_type) > 0

    def test_tracked_set_fields_have_change_types(self) -> None:
        """All tracked set fields should have a change type."""
        for field, change_type in TRACKED_SET_FIELDS.items():
            assert isinstance(change_type, str)
            assert len(change_type) > 0

    def test_key_fields_tracked(self) -> None:
        """Key recruiting fields should be tracked."""
        # Salary is critical
        assert "salaryUpperBound" in TRACKED_FIELDS
        assert "salaryLowerBound" in TRACKED_FIELDS

        # Fee is critical for headhunters
        assert "percent_fee" in TRACKED_FIELDS

        # Headcount affects opportunity size
        assert "hiring_count" in TRACKED_FIELDS

        # Competition matters
        assert "approved_recruiters_count" in TRACKED_FIELDS

        # Location changes matter
        assert "locations" in TRACKED_SET_FIELDS
