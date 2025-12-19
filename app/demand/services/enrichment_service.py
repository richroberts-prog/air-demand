"""LLM enrichment service wrapper.

Provides business logic wrapper around enrichment operations with timeout protection.
"""

import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.monitoring import get_error_aggregator
from app.demand.enrichment import (
    enrich_company_from_role_data,
    get_cached_enrichment,
    should_enrich,
)
from app.demand.models import CompanyEnrichment

logger = get_logger(__name__)


class EnrichmentService:
    """Service for LLM enrichment operations.

    Provides wrapper around existing enrichment functions with
    timeout protection and error handling.
    """

    async def should_enrich(
        self, deterministic_excitement_score: float, qualification_tier: str | None
    ) -> bool:
        """Determine if a company should be enriched with LLM.

        Only enriches when:
        1. Role is QUALIFIED or MAYBE tier
        2. Deterministic excitement score is in uncertain range (0.50-0.70)

        Args:
            deterministic_excitement_score: Score from scoring.py
            qualification_tier: Role qualification tier

        Returns:
            True if enrichment should be performed
        """
        return await should_enrich(deterministic_excitement_score, qualification_tier)

    async def get_cached(self, db: AsyncSession, company_name: str) -> CompanyEnrichment | None:
        """Get cached enrichment for a company.

        Args:
            db: Database session
            company_name: Company name (will be normalized)

        Returns:
            Cached CompanyEnrichment or None if not found
        """
        return await get_cached_enrichment(db, company_name)

    async def enrich_company(
        self, role_data: dict[str, Any], db: AsyncSession
    ) -> CompanyEnrichment | None:
        """Enrich company from role data with LLM and timeout protection.

        Wraps LLM call in asyncio.wait_for() to enforce timeout.
        Handles TimeoutError with appropriate logging and error tracking.

        Args:
            role_data: Raw tRPC response for a role
            db: Database session

        Returns:
            CompanyEnrichment or None if failed/timeout
        """
        settings = get_settings()
        error_aggregator = get_error_aggregator()
        company = role_data.get("company", {})
        company_name = company.get("name", "")

        try:
            # Use timeout protection for LLM call
            enrichment = await asyncio.wait_for(
                enrich_company_from_role_data(role_data, db),
                timeout=settings.llm_timeout,
            )
            return enrichment
        except TimeoutError:
            logger.error(
                "jobs.enrichment_service.timeout",
                company=company_name,
                timeout=settings.llm_timeout,
            )
            # Record timeout error for monitoring
            error_aggregator.record_error(
                "enrichment_timeout",
                {
                    "company": company_name,
                    "timeout_seconds": settings.llm_timeout,
                },
            )
            return None
        except Exception as e:
            logger.error(
                "jobs.enrichment_service.enrichment_failed",
                company=company_name,
                error=str(e),
                exc_info=True,
            )
            # Record enrichment error for monitoring
            error_type = "enrichment_api_error" if "API" in str(e) else "enrichment_parse_error"
            error_aggregator.record_error(
                error_type,
                {
                    "company": company_name,
                    "error": str(e),
                },
            )
            return None
