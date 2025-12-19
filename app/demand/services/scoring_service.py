"""Scoring service wrapper.

Provides business logic wrapper around scoring operations.
"""

from typing import Any

from app.core.logging import get_logger
from app.demand.scoring import calculate_scores, score_excitement_deterministic

logger = get_logger(__name__)


class ScoringService:
    """Service for role scoring operations.

    Provides wrapper around scoring package functions for
    calculating engineer, headhunter, excitement, and combined scores.
    """

    def calculate_all_scores(
        self, role_data: dict[str, Any], enrichment_score: float | None = None
    ) -> dict[str, Any]:
        """Calculate all scores for a role.

        Args:
            role_data: Raw tRPC response for a role
            enrichment_score: Optional LLM enrichment score (overrides deterministic)

        Returns:
            Dict with keys: engineer_score, headhunter_score, excitement_score,
            combined_score, score_breakdown
        """
        return calculate_scores(role_data, enrichment_score=enrichment_score)

    def score_excitement_deterministic(
        self,
        company_name: str,
        investors: list[str],
        funding_amount: str | None,
        funding_stage: str | None,
        industries: list[str],
        founding_year: int | None,
        company_size: int | None,
        title: str | None,
    ) -> tuple[float, list[str]]:
        """Calculate deterministic excitement score.

        Args:
            company_name: Company name
            investors: List of investor names
            funding_amount: Total funding raised (e.g., "$17.3M")
            funding_stage: Current funding stage (e.g., "SERIES_A")
            industries: List of industries
            founding_year: Year company was founded
            company_size: Number of employees
            title: Role title

        Returns:
            Tuple of (excitement_score, breakdown_dict)
        """
        return score_excitement_deterministic(
            company_name=company_name,
            investors=investors,
            funding_amount=funding_amount,
            funding_stage=funding_stage,
            industries=industries,
            founding_year=founding_year,
            company_size=company_size,
            title=title,
        )
