"""Profile generation service - orchestrates detail fetching + LLM extraction."""

from datetime import UTC, datetime

from playwright.async_api import BrowserContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.demand.briefing_extraction import EXTRACTION_MODEL, generate_profile
from app.demand.models import Role, RoleBriefing
from app.demand.scraper.client import get_role_detail

logger = get_logger(__name__)


class BriefingService:
    """Service for profile generation and caching."""

    async def regenerate_from_stored_data(
        self,
        db: AsyncSession,
        paraform_id: str,
        role: Role,
    ) -> RoleBriefing | None:
        """Regenerate profile from stored detail_raw_response (no scraping).

        Useful for:
        - Testing new extraction prompts
        - Upgrading to new models
        - Fixing extraction bugs
        - Iterating on profile structure

        Args:
            db: Database session
            paraform_id: Role ID
            role: Role instance (for combined_score)

        Returns:
            Updated RoleBriefing or None if briefing doesn't exist
        """
        # Load existing briefing with raw data
        stmt = select(RoleBriefing).where(RoleBriefing.paraform_id == paraform_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            logger.warning(
                "jobs.profile.regenerate_not_found",
                paraform_id=paraform_id,
                reason="No existing briefing to regenerate from",
            )
            return None

        logger.info("jobs.profile.regenerate_started", paraform_id=paraform_id)

        try:
            # Use stored raw data (no scraping needed!)
            detail_response = existing.detail_raw_response
            meeting_data = existing.meeting_data

            # Regenerate profile with current extraction logic
            profile = await generate_profile(paraform_id, detail_response, meeting_data)

            # Update profile data
            now = datetime.now(UTC)
            existing.profile_data = profile.model_dump(mode="json")
            existing.score_at_enrichment = role.combined_score or 0.0
            existing.enriched_at = now
            existing.model_version = EXTRACTION_MODEL
            existing.updated_at = now

            # Update old fields for backwards compatibility
            existing.pitch_summary = profile.role.core_responsibility or ""
            existing.requirements_must_have = profile.must_haves
            existing.requirements_nice_to_have = profile.nice_to_haves
            existing.interview_stages = profile.interview.stages
            existing.interview_prep_notes = profile.interview.prep_needed
            existing.red_flags = profile.red_flags

            await db.flush()

            logger.info("jobs.profile.regenerated", paraform_id=paraform_id)
            return existing

        except Exception as e:
            logger.error(
                "jobs.profile.regenerate_failed",
                paraform_id=paraform_id,
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_or_create_briefing(
        self,
        db: AsyncSession,
        context: BrowserContext,
        paraform_id: str,
        role: Role,
    ) -> RoleBriefing | None:
        """Get cached briefing or generate new profile.

        Args:
            db: Database session
            context: Playwright browser context (for API calls)
            paraform_id: Role ID
            role: Role instance (for combined_score)

        Returns:
            RoleBriefing or None if generation fails
        """
        # Check cache
        stmt = select(RoleBriefing).where(RoleBriefing.paraform_id == paraform_id)
        result = await db.execute(stmt)
        cached = result.scalar_one_or_none()

        if cached:
            logger.info("jobs.profile.cache_hit", paraform_id=paraform_id)
            return cached

        logger.info("jobs.profile.generation_started", paraform_id=paraform_id)

        try:
            # Fetch detail data
            detail_response = await get_role_detail(context, paraform_id)
            # Skip meetings for now - 401 errors and not used in extraction yet
            meeting_data = None

            # Generate PROFILE (not briefing)
            profile = await generate_profile(paraform_id, detail_response, meeting_data)

            # Store in database
            now = datetime.now(UTC)
            briefing = RoleBriefing(
                paraform_id=paraform_id,
                detail_raw_response=detail_response,
                meeting_data=meeting_data,
                profile_data=profile.model_dump(mode="json"),  # NEW: Store as JSONB
                # OLD FIELDS: Set to defaults for backwards compatibility during transition
                pitch_summary=profile.role.core_responsibility or "",
                key_selling_points=[],
                day_to_day=None,
                requirements_must_have=profile.must_haves,
                requirements_nice_to_have=profile.nice_to_haves,
                interview_stages=profile.interview.stages,
                interview_timeline=None,
                interview_prep_notes=profile.interview.prep_needed,
                application_questions=[],
                info_to_gather=[],
                red_flags=profile.red_flags,
                score_at_enrichment=role.combined_score or 0.0,
                enriched_at=now,
                model_version=EXTRACTION_MODEL,
                created_at=now,
                updated_at=now,
            )

            db.add(briefing)
            await db.flush()

            logger.info("jobs.profile.cached", paraform_id=paraform_id, briefing_id=briefing.id)
            return briefing

        except Exception as e:
            logger.error(
                "jobs.profile.generation_failed",
                paraform_id=paraform_id,
                error=str(e),
                exc_info=True,
            )
            return None  # Graceful degradation - don't crash scraper
