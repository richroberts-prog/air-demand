"""Orchestrator for Paraform scraping workflow - thin wrapper over ScraperService.

This module is kept for backward compatibility with existing imports.
The actual orchestration logic now lives in ScraperService.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.demand.models import RoleScrapeRun
from app.demand.services import (
    EnrichmentService,
    QualificationService,
    ScoringService,
    ScraperService,
)

logger = get_logger(__name__)


async def run_scrape(
    db: AsyncSession,
    triggered_by: str = "manual",
) -> RoleScrapeRun:
    """Execute Paraform scrape workflow (thin wrapper over ScraperService).

    This function is kept for backward compatibility with existing imports.
    The actual orchestration logic now lives in ScraperService.

    Args:
        db: Database session
        triggered_by: How scrape was triggered ('manual', 'scheduler', 'api')

    Returns:
        Completed RoleScrapeRun record with results
    """
    # Instantiate services
    qualification_service = QualificationService()
    enrichment_service = EnrichmentService()
    scoring_service = ScoringService()
    scraper_service = ScraperService(
        qualification=qualification_service,
        enrichment=enrichment_service,
        scoring=scoring_service,
    )

    # Delegate to service
    return await scraper_service.run_full_scrape(db, triggered_by)
