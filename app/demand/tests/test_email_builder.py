"""Tests for digest email template builder."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.demand.email_builder import DigestEmailBuilder
from app.shared.constants import TIER_1_INVESTORS, TIER_2_INVESTORS


# Mock Role data for testing
class MockRole:
    """Mock Role object for template testing."""

    def __init__(
        self,
        title: str = "Senior Backend Engineer",
        company_name: str = "TechCorp",
        paraform_url: str = "https://paraform.com/role/123",
        combined_score: float | None = 0.85,
        engineer_score: float | None = 0.90,
        headhunter_score: float | None = 0.80,
        qualification_tier: str = "QUALIFIED",
        salary_lower: int | None = 150000,
        salary_upper: int | None = 225000,
        role_types: list[str] | None = None,
        raw_response: dict[str, Any] | None = None,
    ):
        self.title = title
        self.company_name = company_name
        self.paraform_url = paraform_url
        self.combined_score = combined_score
        self.engineer_score = engineer_score
        self.headhunter_score = headhunter_score
        self.qualification_tier = qualification_tier
        self.salary_lower = salary_lower
        self.salary_upper = salary_upper
        self.role_types = role_types or ["backend_engineer"]
        self.raw_response = raw_response or {
            "posted_at": "2024-12-09T10:00:00Z",
            "hiring_count": 2,
            "percent_fee": 15.0,
            "investors": ["Sequoia Capital", "Andreessen Horowitz"],
            "company": {
                "fundingAmount": "$10.7M",
                "industries": ["fintech"],
                "company_metadata": {"last_funding_round": "SERIES_A"},
            },
        }


@pytest.fixture
def template_dir() -> Path:
    """Get the template directory path."""
    return Path(__file__).parent.parent / "templates"


@pytest.fixture
def builder(template_dir: Path) -> DigestEmailBuilder:
    """Create a DigestEmailBuilder instance."""
    return DigestEmailBuilder(template_dir)


@pytest.fixture
def sample_roles() -> list[MockRole]:
    """Create sample roles for testing."""
    return [
        MockRole(
            title="Senior Backend Engineer",
            company_name="TechCorp",
            combined_score=0.92,
            engineer_score=0.95,
            headhunter_score=0.89,
        ),
        MockRole(
            title="Full Stack Engineer",
            company_name="StartupCo",
            combined_score=0.78,
            engineer_score=0.80,
            headhunter_score=0.76,
            role_types=["full_stack_engineer"],
        ),
        MockRole(
            title="ML Engineer",
            company_name="AILabs",
            combined_score=0.65,
            engineer_score=0.70,
            headhunter_score=0.60,
            role_types=["ml_engineer"],
        ),
    ]


@pytest.fixture
def base_context() -> dict[str, Any]:
    """Create base template context."""
    from app.shared.constants import TIER_1_INVESTORS, TIER_2_INVESTORS

    return {
        "since": datetime(2024, 12, 8, 10, 0, 0, tzinfo=UTC),
        "until": datetime(2024, 12, 9, 10, 0, 0, tzinfo=UTC),
        "qualified_count": 0,
        "tier_1_investors": set(TIER_1_INVESTORS),
        "tier_2_investors": set(TIER_2_INVESTORS),
        "dashboard_url": "http://localhost:3000",
        "role_trends": {},
    }


def test_digest_email_builder_initialization(builder: DigestEmailBuilder) -> None:
    """Test that DigestEmailBuilder initializes correctly."""
    assert builder.env is not None
    assert "format_salary" in builder.env.filters
    assert "format_funding" in builder.env.filters
    assert "format_date" in builder.env.filters
    assert "format_score" in builder.env.filters
    assert "format_stage" in builder.env.filters
    assert "format_industry" in builder.env.filters
    assert "format_role_type" in builder.env.filters
    assert "format_hiring" in builder.env.filters
    assert "format_fee" in builder.env.filters
    assert "get_investor_short" in builder.env.filters
    assert "normalize_investor" in builder.env.filters


def test_build_html_with_roles(
    builder: DigestEmailBuilder, sample_roles: list[MockRole], base_context: dict[str, Any]
) -> None:
    """Test HTML rendering with sample roles."""
    context = {
        **base_context,
        "roles": sample_roles,
        "total_count": len(sample_roles),
    }

    html = builder.build_html(context)

    # Check structure
    assert "<!DOCTYPE html>" in html
    assert "AI Recruiter Digest" in html

    # Check roles rendered
    assert "TechCorp" in html
    assert "StartupCo" in html
    assert "AILabs" in html

    # Check scores
    assert "92" in html or "0.92" in html  # High score
    assert "78" in html or "0.78" in html  # Medium score
    assert "65" in html or "0.65" in html  # Low score


def test_build_html_empty_roles(builder: DigestEmailBuilder, base_context: dict[str, Any]) -> None:
    """Test HTML rendering with no roles."""
    context = {
        **base_context,
        "roles": [],
        "total_count": 0,
    }

    html = builder.build_html(context)

    # Should render empty state
    assert "No roles posted in last 24 hours" in html
    assert "AI Recruiter Digest" in html


def test_build_text_with_roles(
    builder: DigestEmailBuilder, sample_roles: list[MockRole], base_context: dict[str, Any]
) -> None:
    """Test text rendering with sample roles."""
    context = {
        **base_context,
        "roles": sample_roles,
        "total_count": len(sample_roles),
    }

    text = builder.build_text(context)

    # Check structure
    assert "AI Recruiter Digest" in text
    assert "=" * 40 in text
    assert "ROLES POSTED YESTERDAY" in text

    # Check roles
    assert "TechCorp" in text
    assert "StartupCo" in text
    assert "Senior Backend Engineer" in text


def test_build_text_empty_roles(builder: DigestEmailBuilder, base_context: dict[str, Any]) -> None:
    """Test text rendering with no roles."""
    context = {
        **base_context,
        "roles": [],
        "total_count": 0,
    }

    text = builder.build_text(context)

    # Should render empty state
    assert "No roles posted in last 24 hours" in text


def test_custom_filters_registered(builder: DigestEmailBuilder) -> None:
    """Test that all custom filters are accessible in templates."""
    # Test salary filter
    salary_filter = builder.env.filters["format_salary"]
    assert salary_filter(150000, 225000) == "225"

    # Test score filter
    score_filter = builder.env.filters["format_score"]
    assert score_filter(0.85) == "85"
    assert score_filter(None) == "—"


def test_score_cell_rendering_high_score(
    builder: DigestEmailBuilder, base_context: dict[str, Any]
) -> None:
    """Test score cell partial with high score (≥0.85)."""
    role = MockRole(combined_score=0.92)
    context = {
        **base_context,
        "roles": [role],
        "total_count": 1,
    }

    html = builder.build_html(context)

    # High scores should have green background
    assert "#dcfce7" in html  # Green background
    assert "92" in html


def test_score_cell_rendering_medium_score(
    builder: DigestEmailBuilder, base_context: dict[str, Any]
) -> None:
    """Test score cell partial with medium score (≥0.70, <0.85)."""
    role = MockRole(combined_score=0.75)
    context = {
        **base_context,
        "roles": [role],
        "total_count": 1,
    }

    html = builder.build_html(context)

    # Medium scores should have blue background
    assert "#dbeafe" in html  # Blue background
    assert "75" in html


def test_score_cell_rendering_low_score(
    builder: DigestEmailBuilder, base_context: dict[str, Any]
) -> None:
    """Test score cell partial with low score (<0.70)."""
    role = MockRole(combined_score=0.55)
    context = {
        **base_context,
        "roles": [role],
        "total_count": 1,
    }

    html = builder.build_html(context)

    # Low scores should be plain text
    assert "55" in html


def test_score_cell_rendering_none(
    builder: DigestEmailBuilder, base_context: dict[str, Any]
) -> None:
    """Test score cell partial with None score."""
    role = MockRole(combined_score=None)
    context = {
        **base_context,
        "roles": [role],
        "total_count": 1,
    }

    html = builder.build_html(context)

    # None scores should show em dash
    assert "—" in html


def test_investor_badge_rendering_tier1(
    builder: DigestEmailBuilder, base_context: dict[str, Any]
) -> None:
    """Test investor badge with Tier 1 investor."""
    role = MockRole()
    role.raw_response["investors"] = ["Sequoia Capital"]
    context = {
        **base_context,
        "roles": [role],
        "total_count": 1,
    }

    html = builder.build_html(context)

    # Should show Sequoia with green badge
    assert "Sequoia" in html
    assert "#dcfce7" in html  # Tier 1 green


def test_investor_badge_rendering_tier2(
    builder: DigestEmailBuilder, base_context: dict[str, Any]
) -> None:
    """Test investor badge with Tier 2 investor."""
    role = MockRole()
    role.raw_response["investors"] = ["First Round Capital"]
    context = {
        **base_context,
        "roles": [role],
        "total_count": 1,
    }

    html = builder.build_html(context)

    # Should show First Round with blue badge
    assert "First Round" in html
    assert "#dbeafe" in html  # Tier 2 blue


def test_investor_badge_rendering_none(
    builder: DigestEmailBuilder, base_context: dict[str, Any]
) -> None:
    """Test investor badge with no notable investors."""
    role = MockRole()
    role.raw_response["investors"] = ["Random VC"]
    context = {
        **base_context,
        "roles": [role],
        "total_count": 1,
    }

    html = builder.build_html(context)

    # Should show em dash when no tier 1/2 investors
    # Just check the structure is present
    assert "TechCorp" in html


def test_null_handling_in_templates(
    builder: DigestEmailBuilder, base_context: dict[str, Any]
) -> None:
    """Test that templates handle null/missing fields gracefully."""
    role = MockRole()
    # Remove fields to test null handling
    role.raw_response = {
        "investors": [],
        "company": {},
    }
    role.salary_upper = None
    role.engineer_score = None

    context = {
        **base_context,
        "roles": [role],
        "total_count": 1,
    }

    # Should not raise exception
    html = builder.build_html(context)
    assert "TechCorp" in html

    text = builder.build_text(context)
    assert "TechCorp" in text


def test_e2e_digest_formatting(builder: DigestEmailBuilder) -> None:
    """E2E test: Verify new digest formatting (date MM-DD, funding integer only)."""

    # Create role with specific date and funding
    role = MockRole(
        company_name="TestCorp",
        raw_response={
            "posted_at": "2024-12-09T10:00:00Z",  # Should show as "12-09"
            "hiring_count": 3,
            "percent_fee": 15.5,
            "investors": ["Sequoia Capital"],
            "locations": ["new_york"],
            "workplace_type": "On-site",
            "company": {
                "fundingAmount": "$10.7M",  # Should show as "11" (rounded from 10.7)
                "industries": ["fintech"],
                "company_metadata": {"last_funding_round": "SERIES_A"},
            },
        },
    )

    context = {
        "roles": [role],
        "total_count": 1,
        "dashboard_url": "http://localhost:3000",
        "tier_1_investors": TIER_1_INVESTORS,
        "tier_2_investors": TIER_2_INVESTORS,
    }

    # Build HTML
    html = builder.build_html(context)

    # Verify date formatting (MM-DD format)
    assert "12-09" in html, "Posted date should be in MM-DD format"
    assert "2024-12-09" not in html, "Full ISO date should not appear in digest"

    # Verify funding formatting (integer only, no M suffix)
    # The template shows funding in a table cell
    # $10.7M should be formatted as "11" (rounded)
    import re

    # Check for "11" as a standalone number in a table cell
    funding_cells = re.findall(
        r'<td style="[^"]*text-align: right[^"]*"[^>]*>(.*?)</td>', html, re.DOTALL
    )
    funding_values = [cell.strip() for cell in funding_cells]
    assert "11" in funding_values, (
        f"Funding should show as integer '11', but found: {funding_values}"
    )
    assert ".7M" not in html, "Funding should not have decimal or M suffix"
    assert "$10.7M" not in html, "Funding should not show raw input"

    # Verify investor is shown (only 1)
    assert "Sequoia" in html or "SEQ" in html, "Should show Sequoia investor"

    print("\n✓ E2E test passed:")
    print("  - Date format: MM-DD (12-09)")
    print("  - Funding format: integer only (11)")
    print("  - Investor: showing 1 investor only")


def test_funding_formats_edge_cases(builder: DigestEmailBuilder) -> None:
    """Test edge cases for funding formatting."""
    import re

    test_cases = [
        ("$70M", "70"),  # Whole millions
        ("$1.5B", "1500"),  # Billions to millions
        ("$231M", "231"),  # Large millions
    ]

    for funding_input, expected_output in test_cases:
        role = MockRole(
            raw_response={
                "posted_at": "2024-12-09T10:00:00Z",
                "hiring_count": 1,
                "percent_fee": 15.0,
                "investors": [],
                "company": {
                    "fundingAmount": funding_input,
                    "company_metadata": {},
                },
            },
        )

        context = {
            "roles": [role],
            "total_count": 1,
            "dashboard_url": "http://localhost:3000",
            "tier_1_investors": TIER_1_INVESTORS,
            "tier_2_investors": TIER_2_INVESTORS,
        }

        html = builder.build_html(context)

        # Check that the expected output appears in right-aligned cells (funding column)
        funding_cells = re.findall(
            r'<td style="[^"]*text-align: right[^"]*"[^>]*>(.*?)</td>', html, re.DOTALL
        )
        funding_values = [cell.strip() for cell in funding_cells]
        assert expected_output in funding_values, (
            f"Funding {funding_input} should format as {expected_output}, but found: {funding_values}"
        )


def test_date_formats_edge_cases(builder: DigestEmailBuilder) -> None:
    """Test edge cases for date formatting."""

    test_cases = [
        ("2024-01-01T00:00:00Z", "01-01"),  # New Year
        ("2024-12-31T23:59:59Z", "12-31"),  # Year end
        ("2024-07-04T12:00:00Z", "07-04"),  # Mid-year
    ]

    for date_input, expected_output in test_cases:
        role = MockRole(
            raw_response={
                "posted_at": date_input,
                "hiring_count": 1,
                "percent_fee": 15.0,
                "investors": [],
                "company": {
                    "fundingAmount": "$10M",
                    "company_metadata": {},
                },
            },
        )

        context = {
            "roles": [role],
            "total_count": 1,
            "dashboard_url": "http://localhost:3000",
            "tier_1_investors": TIER_1_INVESTORS,
            "tier_2_investors": TIER_2_INVESTORS,
        }

        html = builder.build_html(context)

        # Check that the expected date format appears
        assert expected_output in html, f"Date {date_input} should format as {expected_output}"
