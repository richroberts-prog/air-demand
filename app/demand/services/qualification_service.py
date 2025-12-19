"""Qualification business logic service.

Provides qualification and requalification operations for roles.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.demand.enrichment import (
    enrich_company_from_role_data,
    get_cached_enrichment,
    should_enrich,
)
from app.demand.models import Role
from app.demand.qualification import qualify_role
from app.demand.scoring import calculate_scores, score_excitement_deterministic

logger = get_logger(__name__)


class QualificationService:
    """Service for role qualification operations.

    Provides business logic for qualifying and requalifying roles
    based on stored raw_response data.
    """

    async def requalify_all_roles(self, db: AsyncSession) -> dict[str, int | str]:
        """Re-run qualification on all ACTIVE roles using stored raw_response.

        This is faster than a full scrape when you just want to update
        qualification logic without re-fetching from Paraform.

        Args:
            db: Database session

        Returns:
            Stats dict with keys: message, total, qualified, maybe, skip, changed
        """
        logger.info("jobs.qualification_service.requalify_started")

        # Get all ACTIVE roles
        stmt = select(Role).where(Role.lifecycle_status == "ACTIVE")
        result = await db.execute(stmt)
        roles = result.scalars().all()

        total = len(roles)
        qualified = 0
        maybe = 0
        skip = 0
        changed = 0

        for role in roles:
            old_tier = role.qualification_tier
            role_data = role.raw_response

            # Re-run qualification on stored raw_response
            qualification = qualify_role(role_data)
            role.is_qualified = qualification.is_qualified
            role.qualification_tier = qualification.tier
            role.qualification_reasons = qualification.reasons
            role.disqualification_reasons = qualification.disqualifications

            if qualification.tier == "QUALIFIED":
                qualified += 1
            elif qualification.tier == "MAYBE":
                maybe += 1
            else:
                skip += 1

            if old_tier != qualification.tier:
                changed += 1

            # Calculate scores
            company = role_data.get("company", {})
            company_name = company.get("name", "")

            # Get deterministic excitement score first
            excitement, _ = score_excitement_deterministic(
                company_name=company_name,
                investors=role_data.get("investors", []),
                funding_amount=company.get("fundingAmount"),
                funding_stage=company.get("company_metadata", {}).get("last_funding_round"),
                industries=company.get("industries", []),
                founding_year=company.get("foundingYear"),
                company_size=company.get("size"),
                title=role_data.get("name"),
            )

            # Check if we need LLM enrichment for this company
            enrichment_score: float | None = None
            if await should_enrich(excitement, qualification.tier):
                # Check cache first
                cached = await get_cached_enrichment(db, company_name)
                if cached:
                    enrichment_score = cached.excitement_score
                else:
                    # Perform LLM enrichment
                    try:
                        enrichment = await enrich_company_from_role_data(role_data, db)
                        if enrichment:
                            enrichment_score = enrichment.excitement_score
                    except Exception as e:
                        logger.warning(
                            "jobs.qualification_service.enrichment_failed",
                            company=company_name,
                            error=str(e),
                        )

            # Calculate all scores
            scores = calculate_scores(role_data, enrichment_score=enrichment_score)
            role.engineer_score = scores["engineer_score"]
            role.headhunter_score = scores["headhunter_score"]
            role.excitement_score = scores["excitement_score"]
            role.combined_score = scores["combined_score"]
            role.score_breakdown = scores["score_breakdown"]

        await db.commit()

        logger.info(
            "jobs.qualification_service.requalify_completed",
            total=total,
            qualified=qualified,
            maybe=maybe,
            skip=skip,
            changed=changed,
        )

        return {
            "message": "Requalification complete",
            "total": total,
            "qualified": qualified,
            "maybe": maybe,
            "skip": skip,
            "changed": changed,
        }
