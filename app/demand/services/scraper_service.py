"""Scraper workflow orchestration service.

Provides business logic for the full scraping workflow including
authentication, role fetching, qualification, enrichment, and scoring.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.demand.models import Role, RoleScrapeRun
from app.demand.qualification import qualify_role
from app.demand.role_enrichment import enrich_role_from_html, merge_enrichment_into_role_data
from app.demand.scraper.auth import get_session
from app.demand.scraper.client import browse_roles, get_role_detail_simple
from app.demand.scraper.extractors import extract_roles_from_browse
from app.demand.services.enrichment_service import EnrichmentService
from app.demand.services.qualification_service import QualificationService
from app.demand.services.scoring_service import ScoringService
from app.demand.temporal import (
    create_snapshot,
    detect_changes,
    mark_disappeared_roles,
    mark_reappeared_role,
)

logger = get_logger(__name__)


class ScraperService:
    """Service for scraper workflow orchestration.

    Coordinates the full scraping workflow by delegating to specialized services
    for qualification, enrichment, and scoring.
    """

    def __init__(
        self,
        qualification: QualificationService,
        enrichment: EnrichmentService,
        scoring: ScoringService,
    ) -> None:
        """Initialize scraper service with dependencies.

        Args:
            qualification: Qualification service
            enrichment: Enrichment service
            scoring: Scoring service
        """
        self.qualification = qualification
        self.enrichment = enrichment
        self.scoring = scoring

    async def _upsert_role(
        self,
        db: AsyncSession,
        paraform_id: str,
        raw_response: dict[str, Any],
    ) -> tuple[Role, bool, dict[str, Any] | None]:
        """Insert or update a role with raw tRPC response.

        Args:
            db: Database session
            paraform_id: Paraform role ID
            raw_response: Full tRPC response for this role

        Returns:
            Tuple of (Role instance, is_new, old_raw_response or None)
        """
        now = datetime.now(UTC)

        # Check if role exists
        stmt = select(Role).where(Role.paraform_id == paraform_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Capture old data for change detection
            old_raw_response = existing.raw_response.copy() if existing.raw_response else None

            # Update existing role
            existing.raw_response = raw_response
            existing.last_seen_at = now
            return existing, False, old_raw_response
        else:
            # Create new role
            role = Role(
                paraform_id=paraform_id,
                raw_response=raw_response,
                first_seen_at=now,
                last_seen_at=now,
                is_qualified=False,
                qualification_tier="SKIP",
                qualification_reasons=[],
                disqualification_reasons=[],
                lifecycle_status="ACTIVE",
            )
            db.add(role)
            return role, True, None

    def _compute_content_hash(self, role_data: dict[str, Any]) -> str:
        """Compute SHA256 hash of content fields to detect changes.

        Only hashes fields that affect qualification/enrichment:
        - company.name, company.fundingAmount, company.industries
        - salaryUpperBound, percent_fee, locations, workplace_type
        - companyTip, selling_points (enrichment sources)
        - role_types, status, not_accepting_recruiters (qualification inputs)

        Excludes volatile fields like timestamps, view counts, badges.

        Args:
            role_data: Raw role data from Paraform API

        Returns:
            SHA256 hex digest of canonical JSON representation
        """
        # Extract stable fields that affect qual/enrichment
        company = role_data.get("company", {})
        stable = {
            # Company fields
            "company_name": company.get("name"),
            "funding_amount": company.get("fundingAmount"),
            "industries": sorted(company.get("industries", [])),
            "company_size": company.get("size"),
            # Role qualification fields
            "salary_upper": role_data.get("salaryUpperBound"),
            "percent_fee": role_data.get("percent_fee"),
            "locations": sorted(role_data.get("locations", [])),
            "workplace_type": role_data.get("workplace_type"),
            "role_types": sorted(role_data.get("role_types", [])),
            "status": role_data.get("status"),
            "not_accepting_recruiters": role_data.get("not_accepting_recruiters"),
            # Enrichment source fields (from detail API)
            "company_tip": role_data.get("companyTip"),
            "selling_points": role_data.get("selling_points"),
        }

        # Sort keys for deterministic hash
        canonical = json.dumps(stable, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    async def run_full_scrape(
        self,
        db: AsyncSession,
        triggered_by: str = "manual",
    ) -> RoleScrapeRun:
        """Execute full Paraform scrape workflow.

        Simple v0.1 flow:
        1. Authenticate
        2. Fetch all roles from Browse API
        3. Save each role's raw_response
        4. Run qualification on each role
        5. Return scrape run stats

        Args:
            db: Database session
            triggered_by: How scrape was triggered ('manual', 'scheduler', 'api')

        Returns:
            Completed RoleScrapeRun record with results
        """
        # Initialize scrape run
        run_id = uuid4()
        started_at = datetime.now(UTC)

        scrape_run = RoleScrapeRun(
            run_id=run_id,
            status="running",
            started_at=started_at,
            triggered_by=triggered_by,
        )
        db.add(scrape_run)
        await db.flush()

        logger.info(
            "jobs.scraper_service.started",
            run_id=str(run_id),
            scrape_run_id=scrape_run.id,
            triggered_by=triggered_by,
        )

        errors: list[str] = []
        roles_found = 0
        new_roles = 0
        updated_roles = 0
        qualified_roles = 0
        changed_roles = 0
        reappeared_roles = 0
        skipped_unchanged = 0
        seen_paraform_ids: set[str] = set()

        try:
            # Step 1: Authenticate
            logger.info("jobs.scraper_service.auth_started", run_id=str(run_id))
            try:
                context = await get_session()
                logger.info("jobs.scraper_service.auth_completed", run_id=str(run_id))
            except Exception as e:
                error_msg = f"Authentication failed: {e}"
                logger.error(
                    "jobs.scraper_service.auth_failed",
                    run_id=str(run_id),
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                errors.append(error_msg)
                raise

            # Step 2: Fetch roles from browse API
            logger.info("jobs.scraper_service.browse_started", run_id=str(run_id))
            try:
                response = await browse_roles(context, filters={})
                raw_roles = extract_roles_from_browse(response)
                roles_found = len(raw_roles)

                logger.info(
                    "jobs.scraper_service.browse_completed",
                    run_id=str(run_id),
                    roles_found=roles_found,
                )
            except Exception as e:
                error_msg = f"Browse API failed: {e}"
                logger.error(
                    "jobs.scraper_service.browse_failed",
                    run_id=str(run_id),
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                errors.append(error_msg)
                raise

            # Step 3: Save each role and run qualification
            logger.info(
                "jobs.scraper_service.ingestion_started",
                run_id=str(run_id),
                roles_count=roles_found,
            )

            for idx, role_data in enumerate(raw_roles, start=1):
                try:
                    paraform_id = role_data.get("id")
                    if not paraform_id:
                        errors.append(f"Role {idx} missing paraform_id")
                        continue

                    # NEW: Compute content hash to detect if role data changed
                    new_hash = self._compute_content_hash(role_data)

                    # NEW: Check if this role exists in database
                    stmt = select(Role).where(Role.paraform_id == paraform_id)
                    result = await db.execute(stmt)
                    existing_role = result.scalar_one_or_none()

                    # NEW: Determine if content changed (trigger detail fetch + enrichment)
                    content_changed = (
                        existing_role is None  # New role, must process
                        or existing_role.content_hash is None  # Old role without hash, backfill
                        or existing_role.content_hash != new_hash  # Content actually changed
                    )

                    # NEW: Track skipped roles for observability
                    if not content_changed:
                        skipped_unchanged += 1

                    # Step 3a: Run initial qualification (before expensive API/LLM calls)
                    initial_qualification = qualify_role(role_data)

                    # Step 3b: Fetch detail + run LLM ONLY if content changed
                    if content_changed and initial_qualification.tier in (
                        "QUALIFIED",
                        "MAYBE",
                        "LOCATION_UNCERTAIN",
                    ):
                        try:
                            detail_response = await get_role_detail_simple(context, paraform_id)
                            detail_data = (
                                detail_response.get("result", {}).get("data", {}).get("json", {})
                            )

                            # Merge enhanced fields into role_data
                            if detail_data:
                                role_data["companyTip"] = detail_data.get("companyTip")
                                role_data["selling_points"] = detail_data.get("selling_points")
                                role_data["equity"] = detail_data.get("equity")
                                role_data["requirements"] = detail_data.get("requirements", [])
                        except Exception as e:
                            logger.warning(
                                "jobs.scraper_service.detail_fetch_failed",
                                role_id=paraform_id,
                                error=str(e),
                            )

                        # Step 3c: Run LLM enrichment to extract intel from HTML
                        company_tip = role_data.get("companyTip")
                        selling_points = role_data.get("selling_points")
                        if company_tip or selling_points:
                            try:
                                role_enrichment = await enrich_role_from_html(
                                    paraform_id, company_tip, selling_points, db
                                )
                                if role_enrichment:
                                    # Merge extracted investors and signals into role_data
                                    role_data = merge_enrichment_into_role_data(
                                        role_data, role_enrichment
                                    )
                            except Exception as e:
                                logger.warning(
                                    "jobs.scraper_service.enrichment_failed",
                                    role_id=paraform_id,
                                    error=str(e),
                                )

                    # Track this role as seen
                    seen_paraform_ids.add(paraform_id)

                    # Save raw response (may include enhanced data for qualified roles)
                    role, is_new, old_raw_response = await self._upsert_role(
                        db, paraform_id, role_data
                    )

                    # Flush to ensure role.id is assigned before creating snapshot
                    await db.flush()

                    if is_new:
                        new_roles += 1
                    else:
                        updated_roles += 1

                        # Check for reappeared role (was FILLED/REMOVED, now back)
                        if role.lifecycle_status != "ACTIVE":
                            reappear_change = await mark_reappeared_role(db, role, scrape_run)
                            if reappear_change:
                                reappeared_roles += 1

                        # Detect changes between old and new data
                        if old_raw_response:
                            role_changes = await detect_changes(
                                db, role, old_raw_response, role_data, scrape_run
                            )
                            if role_changes:
                                changed_roles += 1

                    # Create snapshot for temporal tracking
                    await create_snapshot(db, role, scrape_run, role_data)

                    # Update lifecycle tracking
                    role.last_seen_in_scrape_id = scrape_run.id
                    role.lifecycle_status = "ACTIVE"

                    # NEW: Update content hash after processing
                    role.content_hash = new_hash

                    # Final qualification (with enriched data for qualified roles)
                    qualification = qualify_role(role_data)
                    role.is_qualified = qualification.is_qualified
                    role.qualification_tier = qualification.tier
                    role.qualification_reasons = qualification.reasons
                    role.disqualification_reasons = qualification.disqualifications

                    if qualification.is_qualified:
                        qualified_roles += 1

                    # Calculate scores for all roles (but only enrich qualified ones)
                    company = role_data.get("company", {})
                    company_name = company.get("name", "")

                    # Get deterministic excitement score first
                    excitement, _ = self.scoring.score_excitement_deterministic(
                        company_name=company_name,
                        investors=role_data.get("investors", []),
                        funding_amount=company.get("fundingAmount"),
                        funding_stage=company.get("company_metadata", {}).get("last_funding_round"),
                        industries=company.get("industries", []),
                        founding_year=company.get("foundingYear"),
                        company_size=company.get("size"),
                        title=role_data.get("name") or "",
                    )

                    # Check if we need LLM enrichment for this company
                    enrichment_score: float | None = None
                    if await self.enrichment.should_enrich(excitement, qualification.tier):
                        # Check cache first
                        cached = await self.enrichment.get_cached(db, company_name)
                        if cached:
                            enrichment_score = cached.excitement_score
                        else:
                            # Perform LLM enrichment
                            company_enrichment = await self.enrichment.enrich_company(role_data, db)
                            if company_enrichment:
                                enrichment_score = company_enrichment.excitement_score

                    # Calculate all scores
                    scores = self.scoring.calculate_all_scores(
                        role_data, enrichment_score=enrichment_score
                    )
                    role.engineer_score = scores["engineer_score"]
                    role.headhunter_score = scores["headhunter_score"]
                    role.excitement_score = scores["excitement_score"]
                    role.combined_score = scores["combined_score"]
                    role.score_breakdown = scores["score_breakdown"]

                    # Generate briefing for high-value roles (80+ score)
                    if role.is_qualified and role.combined_score and role.combined_score >= 0.80:
                        logger.info(
                            "jobs.scraper.briefing_triggered",
                            paraform_id=paraform_id,
                            combined_score=role.combined_score,
                        )
                        try:
                            from app.demand.services.briefing_service import BriefingService

                            briefing_service = BriefingService()
                            await briefing_service.get_or_create_briefing(
                                db=db,
                                context=context,
                                paraform_id=paraform_id,
                                role=role,
                            )
                        except Exception as e:
                            logger.error(
                                "jobs.scraper.briefing_failed",
                                paraform_id=paraform_id,
                                error=str(e),
                                exc_info=True,
                            )
                            # Continue - briefing failure shouldn't crash scrape

                    if idx % 100 == 0:
                        logger.info(
                            "jobs.scraper_service.ingestion_progress",
                            run_id=str(run_id),
                            progress=f"{idx}/{roles_found}",
                            qualified=qualified_roles,
                            skipped_unchanged=skipped_unchanged,
                        )

                except Exception as e:
                    error_msg = f"Failed to process role {idx}: {e}"
                    logger.error(
                        "jobs.scraper_service.role_failed",
                        run_id=str(run_id),
                        progress=f"{idx}/{roles_found}",
                        error=str(e),
                        exc_info=True,
                    )
                    errors.append(error_msg)
                    continue

            # Step 4: Mark disappeared roles (not seen in this scrape)
            disappeared_roles = await mark_disappeared_roles(db, scrape_run, seen_paraform_ids)

            await db.commit()

            # Step 5: Update scrape run with results
            completed_at = datetime.now(UTC)
            duration = int((completed_at - started_at).total_seconds())

            scrape_run.status = "completed" if not errors else "completed_with_errors"
            scrape_run.roles_found = roles_found
            scrape_run.new_roles = new_roles
            scrape_run.updated_roles = updated_roles
            scrape_run.qualified_roles = qualified_roles
            scrape_run.skipped_unchanged = skipped_unchanged
            scrape_run.errors = errors
            scrape_run.completed_at = completed_at
            scrape_run.duration_seconds = duration

            await db.flush()

            logger.info(
                "jobs.scraper_service.completed",
                run_id=str(run_id),
                scrape_run_id=scrape_run.id,
                status=scrape_run.status,
                roles_found=roles_found,
                new_roles=new_roles,
                updated_roles=updated_roles,
                qualified_roles=qualified_roles,
                changed_roles=changed_roles,
                disappeared_roles=disappeared_roles,
                reappeared_roles=reappeared_roles,
                skipped_unchanged=skipped_unchanged,
                errors_count=len(errors),
                duration_seconds=duration,
            )

            return scrape_run

        except Exception as e:
            # Fatal error - scrape failed
            completed_at = datetime.now(UTC)
            duration = int((completed_at - started_at).total_seconds())

            scrape_run.status = "failed"
            scrape_run.roles_found = roles_found
            scrape_run.new_roles = new_roles
            scrape_run.updated_roles = updated_roles
            scrape_run.qualified_roles = qualified_roles
            scrape_run.skipped_unchanged = skipped_unchanged
            scrape_run.errors = errors
            scrape_run.completed_at = completed_at
            scrape_run.duration_seconds = duration

            await db.flush()

            logger.error(
                "jobs.scraper_service.failed",
                run_id=str(run_id),
                scrape_run_id=scrape_run.id,
                error=str(e),
                error_type=type(e).__name__,
                roles_found=roles_found,
                errors_count=len(errors),
                duration_seconds=duration,
                exc_info=True,
            )

            raise
