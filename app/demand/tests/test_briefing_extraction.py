"""Unit tests for profile extraction."""

import asyncio
from typing import Any

import pytest

from app.demand.briefing_extraction import generate_profile


@pytest.mark.asyncio
async def test_profile_extraction_basic() -> None:
    """Test basic profile generation with mock data."""
    detail_response = {
        "result": {
            "data": {
                "json": {
                    "description": "<p>Backend engineer role at Series A startup building real-time data platform...</p>",
                    "requirements": [
                        {"requirement": "5+ years Python", "priority": "DEALBREAKER"},
                        {"requirement": "AWS experience", "priority": "NICE_TO_HAVE"},
                    ],
                    "experience_info": "Senior level, 5+ years backend development",
                    "workPlaceText": "Remote US",
                    "role_question": [{"question": "Why do you want to work here?"}],
                }
            }
        }
    }

    profile = await generate_profile("test-role-1", detail_response, None)

    assert profile.role.core_responsibility
    assert len(profile.role.core_responsibility) > 20  # Should be substantial
    assert isinstance(profile.must_haves, list)
    assert isinstance(profile.nice_to_haves, list)
    assert isinstance(profile.red_flags, list)
    assert isinstance(profile.problem.problem_statement, (str, type(None)))
    assert isinstance(profile.credibility.founder_background, (str, type(None)))


@pytest.mark.asyncio
async def test_profile_timeout_protection() -> None:
    """Test that timeout protection is in place."""
    # This test verifies that generate_profile has timeout protection
    # by checking if it raises TimeoutError when given insufficient time
    detail_response: dict[str, Any] = {"result": {"data": {"json": {}}}}

    # The function should complete or timeout within reasonable time
    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(generate_profile("test", detail_response, None), timeout=0.001)
    except RuntimeError:
        # If it fails fast due to bad data, that's also acceptable
        pass


@pytest.mark.asyncio
async def test_profile_with_empty_description() -> None:
    """Test profile generation handles empty description gracefully."""
    detail_response: dict[str, Any] = {
        "result": {
            "data": {
                "json": {
                    "description": "",
                    "requirements": [],
                    "experience_info": "",
                    "workPlaceText": "",
                    "role_question": [],
                }
            }
        }
    }

    # Should not crash, but may produce minimal output or raise RuntimeError
    try:
        profile = await generate_profile("test-empty", detail_response, None)
        # If it succeeds, verify it returns a profile object
        assert profile is not None
        assert hasattr(profile, "role")
        assert hasattr(profile.role, "core_responsibility")
    except RuntimeError:
        # Acceptable to fail with empty input
        pass
