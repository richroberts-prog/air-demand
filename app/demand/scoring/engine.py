"""Scoring engine orchestration.

Combines engineer, headhunter, and excitement scores into a unified result.
This module coordinates all scoring logic and produces the final combined score.
"""

from typing import Any

from app.core.logging import get_logger

from .engineer import calculate_engineer_score
from .excitement import score_excitement_deterministic
from .headhunter import calculate_headhunter_score

logger = get_logger(__name__)


def calculate_scores(
    role_data: dict[str, Any],
    enrichment_score: float | None = None,
) -> dict[str, Any]:
    """Calculate all scores for a role.

    Args:
        role_data: Raw tRPC response for the role
        enrichment_score: Optional LLM-generated excitement score override

    Returns:
        Dict with engineer_score, headhunter_score, excitement_score,
        combined_score, and score_breakdown.
    """
    company = role_data.get("company", {})

    # Engineer score
    eng_result = calculate_engineer_score(role_data)

    # Headhunter score
    hh_result = calculate_headhunter_score(role_data)

    # Excitement score (use enrichment if provided, else deterministic)
    if enrichment_score is not None:
        excitement = enrichment_score
        excitement_signals = ["LLM-enriched score"]
    else:
        excitement, excitement_signals = score_excitement_deterministic(
            company_name=company.get("name", ""),
            investors=role_data.get("investors", []),
            funding_amount=company.get("fundingAmount"),
            funding_stage=company.get("company_metadata", {}).get("last_funding_round"),
            industries=company.get("industries", []),
            founding_year=company.get("foundingYear"),
            company_size=company.get("size"),
            title=role_data.get("name"),
        )

    # Combined score: Engineer (45%) + Headhunter (55%)
    # Slight bias toward headhunter because we need to make placements
    combined = (eng_result.score * 0.45) + (hh_result.score * 0.55)

    # Build full breakdown
    breakdown = {
        "engineer": {
            "score": eng_result.score,
            "breakdown": eng_result.breakdown,
            "signals": eng_result.signals,
        },
        "headhunter": {
            "score": hh_result.score,
            "breakdown": hh_result.breakdown,
            "signals": hh_result.signals,
        },
        "excitement": {
            "score": round(excitement, 2),
            "signals": excitement_signals,
        },
    }

    return {
        "engineer_score": eng_result.score,
        "headhunter_score": hh_result.score,
        "excitement_score": round(excitement, 2),
        "combined_score": round(combined, 2),
        "score_breakdown": breakdown,
    }
