"""Tests for content hash change detection logic."""

from typing import Any

import pytest

from app.demand.services.scraper_service import ScraperService


@pytest.fixture
def scraper_service():
    """Create scraper service for testing hash logic."""
    # Services not needed for hash computation
    return ScraperService(None, None, None)  # type: ignore[arg-type]


def test_content_hash_stable(scraper_service):
    """Same content produces same hash."""
    role1 = {
        "company": {"name": "Acme", "industries": ["fintech"]},
        "salaryUpperBound": 200000,
        "percent_fee": 20,
    }
    role2 = {
        "company": {"name": "Acme", "industries": ["fintech"]},
        "salaryUpperBound": 200000,
        "percent_fee": 20,
    }

    hash1 = scraper_service._compute_content_hash(role1)
    hash2 = scraper_service._compute_content_hash(role2)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest length


def test_content_hash_detects_salary_change(scraper_service):
    """Hash changes when salary changes."""
    role1 = {"company": {"name": "Acme"}, "salaryUpperBound": 200000}
    role2 = {"company": {"name": "Acme"}, "salaryUpperBound": 250000}

    assert scraper_service._compute_content_hash(role1) != scraper_service._compute_content_hash(
        role2
    )


def test_content_hash_detects_location_change(scraper_service):
    """Hash changes when location changes."""
    role1 = {"locations": ["new_york"], "workplace_type": "hybrid"}
    role2 = {"locations": ["remote"], "workplace_type": "remote"}

    assert scraper_service._compute_content_hash(role1) != scraper_service._compute_content_hash(
        role2
    )


def test_content_hash_detects_enrichment_source_change(scraper_service):
    """Hash changes when enrichment sources change."""
    role1 = {"companyTip": "<p>Old tip</p>", "selling_points": "Old points"}
    role2 = {"companyTip": "<p>New tip with investors</p>", "selling_points": "New points"}

    assert scraper_service._compute_content_hash(role1) != scraper_service._compute_content_hash(
        role2
    )


def test_content_hash_ignores_timestamps(scraper_service):
    """Hash stable despite timestamp changes."""
    role1 = {"company": {"name": "Acme"}, "posted_at": "2025-12-15", "updated_at": "2025-12-15"}
    role2 = {"company": {"name": "Acme"}, "posted_at": "2025-12-16", "updated_at": "2025-12-16"}

    assert scraper_service._compute_content_hash(role1) == scraper_service._compute_content_hash(
        role2
    )


def test_content_hash_ignores_view_counts(scraper_service):
    """Hash stable despite view count changes."""
    role1 = {"company": {"name": "Acme"}, "view_count": 100}
    role2 = {"company": {"name": "Acme"}, "view_count": 200}

    assert scraper_service._compute_content_hash(role1) == scraper_service._compute_content_hash(
        role2
    )


def test_content_hash_sorts_lists(scraper_service):
    """Hash stable regardless of list order."""
    role1 = {"company": {"industries": ["fintech", "ai", "saas"]}}
    role2 = {"company": {"industries": ["saas", "fintech", "ai"]}}

    assert scraper_service._compute_content_hash(role1) == scraper_service._compute_content_hash(
        role2
    )


def test_content_hash_handles_missing_fields(scraper_service):
    """Hash handles missing/null fields gracefully."""
    role1: dict[str, Any] = {"company": {"name": "Acme"}}
    role2: dict[str, Any] = {"company": {"name": "Acme", "fundingAmount": None, "industries": []}}

    # Hashes should be stable (no crashes)
    hash1 = scraper_service._compute_content_hash(role1)
    hash2 = scraper_service._compute_content_hash(role2)

    assert isinstance(hash1, str)
    assert isinstance(hash2, str)


def test_content_hash_handles_nested_dicts(scraper_service):
    """Hash correctly processes nested company metadata."""
    role1 = {
        "company": {
            "name": "Acme",
            "fundingAmount": "$10M",
            "industries": ["fintech", "ai"],
            "size": 50,
        }
    }
    role2 = {
        "company": {
            "name": "Acme",
            "fundingAmount": "$10M",
            "industries": ["ai", "fintech"],  # Different order
            "size": 50,
        }
    }

    assert scraper_service._compute_content_hash(role1) == scraper_service._compute_content_hash(
        role2
    )
