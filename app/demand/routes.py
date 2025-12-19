"""API routes for demand feature v0.1.

Endpoints:
- POST /demand/scrape: Manual trigger for Paraform scraping
- GET /demand/roles: List qualified roles with filtering/pagination
- GET /demand/roles/{id}: Get single role details
- GET /demand/roles/new: Get new roles since timestamp
- GET /demand/roles/changes: Get recent role changes
- GET /demand/roles/disappeared: Get disappeared roles
- GET /demand/roles/{id}/history: Get change history for a role
- GET /demand/scrape-runs: List scrape runs
- GET /demand/stats: Get qualification statistics
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, Response
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.demand.models import (
    Role,
    RoleBriefing,
    RoleChange,
    RoleScrapeRun,
    RoleSnapshot,
    UserSettings,
)
from app.demand.schemas import (
    BriefingHeaderMetadata,
    CredibilitySignalsSchema,
    InterviewProcessSchema,
    LastVisitResponse,
    LastVisitUpdate,
    NewRolesResponse,
    ProblemContextSchema,
    QualificationStats,
    RoleBriefingResponse,
    RoleChangeResponse,
    RoleDetail,
    RoleDetailsSchema,
    RoleHistoryResponse,
    RoleListItem,
    RoleListResponse,
    ScrapeRunResponse,
)
from app.demand.services import (
    EnrichmentService,
    QualificationService,
    ScoringService,
    ScraperService,
)
from app.demand.services.interview_trends import get_role_trends

logger = get_logger(__name__)

router = APIRouter(prefix="/demand", tags=["demand"])


# Dependency injection functions for services
def get_qualification_service() -> QualificationService:
    """Get qualification service instance.

    Returns:
        QualificationService instance
    """
    return QualificationService()


def get_scraper_service() -> ScraperService:
    """Get scraper service instance.

    Returns:
        ScraperService instance with all dependencies injected
    """
    return ScraperService(
        qualification=QualificationService(),
        enrichment=EnrichmentService(),
        scoring=ScoringService(),
    )


@router.post("/scrape", status_code=202)
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    service: ScraperService = Depends(get_scraper_service),
) -> dict[str, str]:
    """Manually trigger Paraform scraping.

    Starts scrape in background task and returns immediately.
    Scrape results will be logged and stored in database.

    Returns:
        Acknowledgment message with instructions to check logs.
    """
    logger.info("jobs.routes.manual_scrape_triggered")

    async def scrape_task() -> None:
        """Background task to run scrape."""
        try:
            scrape_run = await service.run_full_scrape(db, triggered_by="api")
            logger.info(
                "jobs.routes.manual_scrape_completed",
                run_id=str(scrape_run.run_id),
                status=scrape_run.status,
                qualified_roles=scrape_run.qualified_roles,
            )
        except Exception as e:
            logger.error(
                "jobs.routes.manual_scrape_failed",
                error=str(e),
                exc_info=True,
            )

    background_tasks.add_task(scrape_task)

    return {
        "message": "Scrape started in background",
        "status": "accepted",
        "note": "Check logs for progress and results",
    }


@router.post("/requalify")
async def requalify_roles(
    db: AsyncSession = Depends(get_db),
    service: QualificationService = Depends(get_qualification_service),
) -> dict[str, int | str]:
    """Re-run qualification on all existing roles using stored raw_response.

    This is faster than a full scrape when you just want to update
    qualification logic without re-fetching from Paraform.

    Returns:
        Stats about requalification results
    """
    logger.info("jobs.routes.requalify_started")
    stats = await service.requalify_all_roles(db)
    logger.info(
        "jobs.routes.requalify_completed", **{k: v for k, v in stats.items() if k != "message"}
    )
    return stats


# ====================
# Temporal Tracking Endpoints (MUST come before /roles/{role_id} to avoid route conflicts)
# ====================


@router.get("/roles/new", response_model=NewRolesResponse)
async def get_new_roles(
    db: AsyncSession = Depends(get_db),
    since: Annotated[
        datetime | None, Query(description="Roles posted after this timestamp")
    ] = None,
    qualified_only: Annotated[bool, Query(description="Only include qualified roles")] = True,
    tiers: Annotated[list[str] | None, Query(description="Filter by specific tiers")] = None,
) -> NewRolesResponse:
    """Get roles posted since a timestamp.

    Uses posted_at (when role was posted on Paraform) for filtering,
    answering questions like "which roles came out this week?"

    Query Parameters:
        since: Only roles posted after this timestamp (default: 24 hours ago)
        qualified_only: Only include QUALIFIED/MAYBE roles (default True, ignored if tiers specified)
        tiers: List of specific tiers to include (overrides qualified_only)

    Returns:
        List of new roles with count
    """
    # Default to 24 hours ago if not specified
    if since is None:
        since = datetime.now(UTC) - timedelta(hours=24)

    logger.info("jobs.api.new_roles_query", since=since.isoformat(), tiers=tiers)

    # Use posted_at from raw_response JSONB (when role was posted on Paraform)
    # This answers "which roles came out this week?" correctly
    # Path: raw_response['posted_at'] (top-level field)
    posted_at_text = Role.raw_response["posted_at"].astext
    posted_at_ts = cast(posted_at_text, TIMESTAMP(timezone=True))

    # Only show live roles (not disappeared)
    stmt = select(Role).where(posted_at_ts > since).where(Role.lifecycle_status == "active")

    # Apply tier filter
    if tiers:
        stmt = stmt.where(Role.qualification_tier.in_(tiers))
    elif qualified_only:
        stmt = stmt.where(Role.qualification_tier.in_(["QUALIFIED", "MAYBE"]))

    stmt = stmt.order_by(posted_at_ts.desc())

    result = await db.execute(stmt)
    roles = result.scalars().all()

    role_items = [RoleListItem.from_role(role) for role in roles]

    logger.info("jobs.api.new_roles_completed", count=len(role_items))

    return NewRolesResponse(
        roles=role_items,
        count=len(role_items),
        since=since,
    )


@router.get("/roles/changes", response_model=list[RoleChangeResponse])
async def get_role_changes(
    db: AsyncSession = Depends(get_db),
    since: Annotated[datetime | None, Query(description="Changes after this timestamp")] = None,
    change_types: Annotated[list[str] | None, Query(description="Filter by change types")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max results")] = 100,
) -> list[RoleChangeResponse]:
    """Get recent role changes.

    Query Parameters:
        since: Only changes after this timestamp (default: 7 days ago)
        change_types: Filter by types (SALARY_INCREASE, FEE_CHANGE, etc.)
        limit: Maximum results to return

    Returns:
        List of changes with role info
    """
    # Default to 7 days ago if not specified
    if since is None:
        since = datetime.now(UTC) - timedelta(days=7)

    logger.info(
        "jobs.api.changes_query",
        since=since.isoformat(),
        change_types=change_types,
        limit=limit,
    )

    stmt = (
        select(RoleChange, Role)
        .join(Role, RoleChange.role_id == Role.id)
        .where(RoleChange.detected_at > since)
    )

    if change_types:
        stmt = stmt.where(RoleChange.change_type.in_(change_types))

    stmt = stmt.order_by(RoleChange.detected_at.desc()).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    changes: list[RoleChangeResponse] = []
    for change, role in rows:
        changes.append(
            RoleChangeResponse(
                id=change.id,
                role_id=change.role_id,
                role_title=role.title,
                company_name=role.company_name,
                change_type=change.change_type,
                field_name=change.field_name,
                old_value=change.old_value,
                new_value=change.new_value,
                detected_at=change.detected_at,
            )
        )

    logger.info("jobs.api.changes_completed", count=len(changes))
    return changes


@router.get("/roles/disappeared", response_model=list[RoleListItem])
async def get_disappeared_roles(
    db: AsyncSession = Depends(get_db),
    since: Annotated[datetime | None, Query(description="Disappeared after this timestamp")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Max results")] = 50,
) -> list[RoleListItem]:
    """Get roles that have disappeared (filled/removed).

    Query Parameters:
        since: Only roles that disappeared after this timestamp
        limit: Maximum results to return

    Returns:
        List of disappeared roles
    """
    logger.info("jobs.api.disappeared_query", since=since.isoformat() if since else None)

    stmt = select(Role).where(Role.lifecycle_status.in_(["FILLED", "REMOVED"]))

    if since:
        stmt = stmt.where(Role.disappeared_at > since)

    stmt = stmt.order_by(Role.disappeared_at.desc()).limit(limit)

    result = await db.execute(stmt)
    roles = result.scalars().all()

    role_items = [RoleListItem.from_role(role) for role in roles]

    logger.info("jobs.api.disappeared_completed", count=len(role_items))
    return role_items


@router.get("/roles/hot", response_model=list[RoleListItem])
async def get_hot_roles(
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=50, description="Max results")] = 20,
) -> list[RoleListItem]:
    """Get roles with surging interview activity (hot roles).

    Returns roles that have had INTERVIEW_INCREASE changes in the last 7 days,
    ordered by change magnitude (new_value - old_value DESC).

    Query Parameters:
        limit: Maximum results to return (default 20, max 50)

    Returns:
        List of hot roles with surging interview activity
    """
    logger.info("jobs.api.hot_roles_query", limit=limit)

    # Query INTERVIEW_INCREASE changes from last 7 days
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)

    stmt = (
        select(RoleChange, Role)
        .join(Role, RoleChange.role_id == Role.id)
        .where(RoleChange.change_type == "INTERVIEW_INCREASE")
        .where(RoleChange.detected_at > seven_days_ago)
        .where(Role.lifecycle_status == "ACTIVE")
        .where(Role.qualification_tier.in_(["QUALIFIED", "MAYBE"]))
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Calculate magnitude and create role items with magnitude data
    role_magnitudes: list[tuple[Role, int]] = []
    for change, role in rows:
        # Parse old and new values to calculate magnitude
        old_val = int(change.old_value) if change.old_value and change.old_value.isdigit() else 0
        new_val = int(change.new_value) if change.new_value and change.new_value.isdigit() else 0
        magnitude = new_val - old_val
        role_magnitudes.append((role, magnitude))

    # Sort by magnitude descending and take top N
    role_magnitudes.sort(key=lambda x: x[1], reverse=True)
    top_roles = [role for role, _ in role_magnitudes[:limit]]

    # Convert to RoleListItem
    role_items = [RoleListItem.from_role(role) for role in top_roles]

    logger.info("jobs.api.hot_roles_completed", count=len(role_items))
    return role_items


@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    response: Response,
    db: AsyncSession = Depends(get_db),
    tier: Annotated[
        str | None, Query(description="Filter by tier (QUALIFIED, MAYBE, SKIP)")
    ] = None,
    qualified_only: Annotated[
        bool, Query(description="Only show qualified roles (QUALIFIED + MAYBE)")
    ] = True,
    search: Annotated[str | None, Query(description="Search in title or company name")] = None,
    min_salary: Annotated[int | None, Query(ge=0, description="Minimum salary upper bound")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000, description="Results per page")] = 50,
) -> RoleListResponse:
    """List roles with filtering and pagination.

    Query Parameters:
        tier: Filter by tier (QUALIFIED, MAYBE, SKIP)
        qualified_only: Only show qualified roles (default True)
        search: Search in role title or company name (JSONB)
        min_salary: Minimum salary upper bound
        page: Page number (default 1)
        page_size: Results per page (max 500, default 50)

    Returns:
        Paginated list of roles
    """
    # Cache for 60 seconds - roles don't change frequently
    response.headers["Cache-Control"] = "public, max-age=60"

    logger.info(
        "jobs.api.roles_query_started",
        tier=tier,
        qualified_only=qualified_only,
        search=search,
        min_salary=min_salary,
        page=page,
        page_size=page_size,
    )

    # Build query - always filter to ACTIVE (live) roles only
    stmt = select(Role).where(Role.lifecycle_status == "ACTIVE")

    # Filter by tier
    if tier:
        stmt = stmt.where(Role.qualification_tier == tier.upper())
    elif qualified_only:
        stmt = stmt.where(Role.qualification_tier.in_(["QUALIFIED", "MAYBE"]))

    # Search in JSONB
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            Role.raw_response["name"].astext.ilike(search_pattern)
            | Role.raw_response["company"]["name"].astext.ilike(search_pattern)
        )

    # Filter by salary (cast JSONB to integer for comparison)
    if min_salary:
        stmt = stmt.where(cast(Role.raw_response["salaryUpperBound"].astext, Integer) >= min_salary)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Role.first_seen_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(stmt)
    roles = list(result.scalars().all())

    # Convert to response schemas
    role_items = [RoleListItem.from_role(role) for role in roles]

    # Check which roles have briefings
    if roles:
        from app.demand.models import RoleBriefing

        paraform_ids = [role.paraform_id for role in roles]
        briefing_stmt = select(RoleBriefing.paraform_id).where(
            RoleBriefing.paraform_id.in_(paraform_ids)
        )
        briefing_result = await db.execute(briefing_stmt)
        briefing_ids = set(briefing_result.scalars().all())

        # Update has_briefing field
        for role_item in role_items:
            role_item.has_briefing = role_item.paraform_id in briefing_ids

    # Calculate trends from recent role changes (last 7 days)
    if roles:
        since = datetime.now(UTC) - timedelta(days=7)
        interview_change_types = [
            "INTERVIEW_INCREASE",
            "INTERVIEW_DECREASE",
            "HIRING_INCREASE",
            "HIRING_DECREASE",
        ]
        role_ids = [r.id for r in roles]
        changes_stmt = (
            select(RoleChange)
            .where(RoleChange.role_id.in_(role_ids))
            .where(RoleChange.detected_at > since)
            .where(RoleChange.change_type.in_(interview_change_types))
        )
        changes_result = await db.execute(changes_stmt)
        all_changes = list(changes_result.scalars().all())

        # Group changes by role_id
        changes_by_role: dict[int, list[RoleChange]] = {}
        for change in all_changes:
            if change.role_id not in changes_by_role:
                changes_by_role[change.role_id] = []
            changes_by_role[change.role_id].append(change)

        # Calculate and assign trends
        trends = get_role_trends(roles, changes_by_role)
        for item in role_items:
            item.trend = trends.get(item.id)

    logger.info("jobs.api.roles_query_completed", count=len(role_items), total=total)

    return RoleListResponse(
        roles=role_items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(role_items)) < total,
    )


@router.get("/roles/{role_id}", response_model=RoleDetail)
async def get_role(
    role_id: Annotated[int, Path(gt=0, description="Role ID")],
    db: AsyncSession = Depends(get_db),
) -> RoleDetail:
    """Get single role by ID with full details.

    Args:
        role_id: Role primary key ID

    Returns:
        Role with full details including raw_response

    Raises:
        HTTPException: 404 if role not found
    """
    logger.info("jobs.api.role_get_started", role_id=role_id)

    stmt = select(Role).where(Role.id == role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if role is None:
        logger.warning("jobs.api.role_not_found", role_id=role_id)
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")

    logger.info("jobs.api.role_get_completed", role_id=role_id)
    return RoleDetail.from_role(role)


@router.get("/scrape-runs", response_model=list[ScrapeRunResponse])
async def list_scrape_runs(
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100, description="Results per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> list[ScrapeRunResponse]:
    """List recent scrape runs with metrics.

    Query Parameters:
        limit: Results per page (max 100, default 50)
        offset: Pagination offset (default 0)

    Returns:
        List of scrape runs ordered by created_at DESC
    """
    logger.info("jobs.api.scrape_runs_query_started", limit=limit, offset=offset)

    stmt = (
        select(RoleScrapeRun).order_by(RoleScrapeRun.created_at.desc()).offset(offset).limit(limit)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()

    results = [ScrapeRunResponse.model_validate(run) for run in runs]

    logger.info("jobs.api.scrape_runs_query_completed", count=len(results))
    return results


@router.get("/stats", response_model=QualificationStats)
async def get_stats(db: AsyncSession = Depends(get_db)) -> QualificationStats:
    """Get role qualification statistics.

    Returns:
        Stats with total, qualified, maybe, skip counts and percentage
    """
    logger.info("jobs.api.stats_query_started")

    # Count by tier (only ACTIVE roles - exclude FILLED/REMOVED)
    total_stmt = select(func.count(Role.id)).where(Role.lifecycle_status == "ACTIVE")
    qualified_stmt = select(func.count(Role.id)).where(
        Role.lifecycle_status == "ACTIVE", Role.qualification_tier == "QUALIFIED"
    )
    maybe_stmt = select(func.count(Role.id)).where(
        Role.lifecycle_status == "ACTIVE", Role.qualification_tier == "MAYBE"
    )
    skip_stmt = select(func.count(Role.id)).where(
        Role.lifecycle_status == "ACTIVE", Role.qualification_tier == "SKIP"
    )

    total = (await db.execute(total_stmt)).scalar() or 0
    qualified = (await db.execute(qualified_stmt)).scalar() or 0
    maybe = (await db.execute(maybe_stmt)).scalar() or 0
    skip = (await db.execute(skip_stmt)).scalar() or 0

    qualified_pct = ((qualified + maybe) / total * 100) if total > 0 else 0.0

    stats = QualificationStats(
        total_roles=total,
        qualified_count=qualified,
        maybe_count=maybe,
        skip_count=skip,
        qualified_percentage=round(qualified_pct, 1),
    )

    logger.info(
        "jobs.api.stats_query_completed",
        total=total,
        qualified=qualified,
        maybe=maybe,
        skip=skip,
    )
    return stats


@router.get("/roles/{role_id}/history", response_model=RoleHistoryResponse)
async def get_role_history(
    role_id: Annotated[int, Path(gt=0, description="Role ID")],
    db: AsyncSession = Depends(get_db),
) -> RoleHistoryResponse:
    """Get change history for a specific role.

    Args:
        role_id: Role primary key ID

    Returns:
        Role with its change history and snapshot count

    Raises:
        HTTPException: 404 if role not found
    """
    logger.info("jobs.api.history_query", role_id=role_id)

    # Get role
    stmt = select(Role).where(Role.id == role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if role is None:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")

    # Get changes
    changes_stmt = (
        select(RoleChange)
        .where(RoleChange.role_id == role_id)
        .order_by(RoleChange.detected_at.desc())
        .limit(100)
    )
    changes_result = await db.execute(changes_stmt)
    changes = changes_result.scalars().all()

    # Get snapshot count
    snapshot_count_stmt = select(func.count(RoleSnapshot.id)).where(RoleSnapshot.role_id == role_id)
    snapshot_count = (await db.execute(snapshot_count_stmt)).scalar() or 0

    change_responses = [
        RoleChangeResponse(
            id=c.id,
            role_id=c.role_id,
            role_title=role.title,
            company_name=role.company_name,
            change_type=c.change_type,
            field_name=c.field_name,
            old_value=c.old_value,
            new_value=c.new_value,
            detected_at=c.detected_at,
        )
        for c in changes
    ]

    logger.info(
        "jobs.api.history_completed",
        role_id=role_id,
        changes=len(change_responses),
        snapshots=snapshot_count,
    )

    return RoleHistoryResponse(
        role=RoleListItem.from_role(role),
        changes=change_responses,
        snapshots_count=snapshot_count,
    )


@router.get("/roles/{paraform_id}/briefing", response_model=RoleBriefingResponse)
async def get_role_briefing(
    paraform_id: str,
    db: AsyncSession = Depends(get_db),
) -> RoleBriefingResponse:
    """Get comprehensive role briefing with profile + header data.

    Returns cached briefing if available, otherwise returns 404.
    Briefings are auto-generated for roles with 80+ combined score during scraping.

    Args:
        paraform_id: Paraform role ID

    Returns:
        Comprehensive briefing with header metadata + profile sections

    Raises:
        HTTPException: 404 if role or briefing not found
    """
    logger.info("jobs.api.briefing_query", paraform_id=paraform_id)

    # Fetch role (for Browse API metadata)
    role_stmt = select(Role).where(Role.paraform_id == paraform_id)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Fetch briefing
    briefing_stmt = select(RoleBriefing).where(RoleBriefing.paraform_id == paraform_id)
    briefing_result = await db.execute(briefing_stmt)
    briefing = briefing_result.scalar_one_or_none()

    if not briefing:
        raise HTTPException(
            status_code=404, detail="Briefing not available (score < 80 or not yet generated)"
        )

    # Build header from Browse API data
    raw = role.raw_response
    salary_lower = raw.get("salaryLowerBound", 0) // 1000
    salary_upper = raw.get("salaryUpperBound", 0) // 1000
    percent_fee = raw.get("percent_fee", 0)
    commission_lower = int(salary_lower * 1000 * percent_fee / 100) // 1000
    commission_upper = int(salary_upper * 1000 * percent_fee / 100) // 1000

    header = BriefingHeaderMetadata(
        company_name=raw.get("company", {}).get("name", "Unknown"),
        company_stage=raw.get("company", {}).get("company_metadata", {}).get("last_funding_round"),
        team_size=raw.get("company", {}).get("size"),
        salary_range=f"${salary_lower}-{salary_upper}K",
        equity=raw.get("equity"),
        location=", ".join(raw.get("locations", [])[:2]),  # First 2 locations
        workplace_type=raw.get("workplace_type"),
        hiring_count=raw.get("hiring_count"),
        interview_stages_count=raw.get("interview_stages"),
        commission_percent=percent_fee,
        commission_amount=f"${commission_lower}-{commission_upper}K"
        if commission_lower > 0
        else None,
    )

    # Parse profile_data JSONB
    profile = briefing.profile_data
    if not profile:
        # Fallback for old briefings without profile_data
        raise HTTPException(
            status_code=404, detail="Briefing not migrated to new format yet (run backfill script)"
        )

    logger.info("jobs.api.briefing_found", paraform_id=paraform_id)

    return RoleBriefingResponse(
        paraform_id=paraform_id,
        header=header,
        problem=ProblemContextSchema(**profile["problem"]),
        credibility=CredibilitySignalsSchema(**profile["credibility"]),
        role=RoleDetailsSchema(**profile["role"]),
        must_haves=profile["must_haves"],
        nice_to_haves=profile["nice_to_haves"],
        interview=InterviewProcessSchema(**profile["interview"]),
        red_flags=profile["red_flags"],
        score_at_enrichment=briefing.score_at_enrichment,
        enriched_at=briefing.enriched_at,
    )


# ====================
# User Settings Endpoints
# ====================


@router.get("/settings/last-visit", response_model=LastVisitResponse)
async def get_last_visit(
    db: AsyncSession = Depends(get_db),
) -> LastVisitResponse:
    """Get the last dashboard visit timestamp.

    Returns:
        Last visit timestamp (or null if never visited)
    """
    stmt = select(UserSettings).where(UserSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings is None:
        return LastVisitResponse(last_visit=None, updated_at=None)

    # Cast to satisfy type checker - at runtime updated_at is just datetime
    updated_at_val: datetime | None = settings.updated_at  # type: ignore[assignment]
    return LastVisitResponse(
        last_visit=settings.last_dashboard_visit,
        updated_at=updated_at_val,
    )


@router.put("/settings/last-visit", response_model=LastVisitResponse)
async def update_last_visit(
    body: LastVisitUpdate,
    db: AsyncSession = Depends(get_db),
) -> LastVisitResponse:
    """Update the last dashboard visit timestamp.

    Args:
        body: New last visit timestamp

    Returns:
        Updated settings
    """
    stmt = select(UserSettings).where(UserSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings is None:
        # Create if doesn't exist
        settings = UserSettings(id=1, last_dashboard_visit=body.last_visit)
        db.add(settings)
    else:
        settings.last_dashboard_visit = body.last_visit

    await db.commit()
    await db.refresh(settings)

    logger.info(
        "jobs.api.last_visit_updated",
        last_visit=body.last_visit.isoformat(),
    )

    # Cast to satisfy type checker - at runtime updated_at is just datetime
    updated_at_val: datetime | None = settings.updated_at  # type: ignore[assignment]
    return LastVisitResponse(
        last_visit=settings.last_dashboard_visit,
        updated_at=updated_at_val,
    )
