"""Temporal tracking for role changes and snapshots.

Provides functions to:
- Create snapshots of role data per scrape run
- Detect changes between scrapes
- Mark roles as disappeared/reappeared
- Query change history
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.demand.models import Role, RoleChange, RoleScrapeRun, RoleSnapshot

logger = get_logger(__name__)


# Fields to track for changes (with their change type mapping)
TRACKED_FIELDS: dict[str, tuple[str, str]] = {
    # field_path: (increase_type, decrease_type) or (change_type, change_type)
    "salaryUpperBound": ("SALARY_INCREASE", "SALARY_DECREASE"),
    "salaryLowerBound": ("SALARY_INCREASE", "SALARY_DECREASE"),
    "percent_fee": ("FEE_CHANGE", "FEE_CHANGE"),
    "hiring_count": ("HEADCOUNT_CHANGE", "HEADCOUNT_CHANGE"),
    "approved_recruiters_count": ("COMPETITION_CHANGE", "COMPETITION_CHANGE"),
    "total_interviewing": ("INTERVIEW_INCREASE", "INTERVIEW_DECREASE"),
    "total_hired": ("HIRING_INCREASE", "HIRING_DECREASE"),
}

# Fields that are tracked as sets (order doesn't matter)
TRACKED_SET_FIELDS: dict[str, str] = {
    "locations": "LOCATION_CHANGE",
}


def _extract_field(data: dict[str, Any], field: str) -> Any:
    """Extract a field from role data, handling nested paths."""
    if "." in field:
        parts = field.split(".")
        value: Any = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value
    return data.get(field)


def _format_value(value: Any) -> str | None:
    """Format a value for storage in the change log."""
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


async def get_latest_snapshot(
    db: AsyncSession,
    role_id: int,
) -> RoleSnapshot | None:
    """Get the most recent snapshot for a role.

    Args:
        db: Database session.
        role_id: Role ID.

    Returns:
        Most recent snapshot or None if no snapshots exist.
    """
    stmt = (
        select(RoleSnapshot)
        .where(RoleSnapshot.role_id == role_id)
        .order_by(RoleSnapshot.scraped_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_snapshot(
    db: AsyncSession,
    role: Role,
    scrape_run: RoleScrapeRun,
    raw_response: dict[str, Any],
) -> RoleSnapshot:
    """Create a snapshot of current role state.

    Args:
        db: Database session.
        role: Role to snapshot.
        scrape_run: Current scrape run.
        raw_response: Raw tRPC response data.

    Returns:
        Created snapshot.
    """
    now = datetime.now(UTC)

    snapshot = RoleSnapshot(
        role_id=role.id,
        scrape_run_id=scrape_run.id,
        raw_response=raw_response,
        salary_upper=raw_response.get("salaryUpperBound"),
        percent_fee=raw_response.get("percent_fee"),
        hiring_count=raw_response.get("hiring_count"),
        scraped_at=now,
    )
    db.add(snapshot)

    logger.debug(
        "jobs.temporal.snapshot_created",
        role_id=role.id,
        scrape_run_id=scrape_run.id,
    )

    return snapshot


async def detect_changes(
    db: AsyncSession,
    role: Role,
    old_data: dict[str, Any] | None,
    new_data: dict[str, Any],
    scrape_run: RoleScrapeRun,
) -> list[RoleChange]:
    """Detect changes between old and new role data.

    Args:
        db: Database session.
        role: Role being checked.
        old_data: Previous raw_response (None if first scrape).
        new_data: New raw_response.
        scrape_run: Current scrape run.

    Returns:
        List of detected changes.
    """
    if old_data is None:
        # First time seeing this role, no changes to detect
        return []

    now = datetime.now(UTC)
    changes: list[RoleChange] = []

    # Check numeric/simple fields
    for field, (increase_type, decrease_type) in TRACKED_FIELDS.items():
        old_val = _extract_field(old_data, field)
        new_val = _extract_field(new_data, field)

        if old_val != new_val and (old_val is not None or new_val is not None):
            # Determine change type based on direction
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                change_type = increase_type if new_val > old_val else decrease_type
            elif old_val is not None and new_val is None:
                # Value disappeared - treat as decrease
                change_type = decrease_type
            elif old_val is None and new_val is not None:
                # Value appeared - treat as increase
                change_type = increase_type
            else:
                change_type = increase_type  # Default to first type for other non-numeric

            change = RoleChange(
                role_id=role.id,
                scrape_run_id=scrape_run.id,
                change_type=change_type,
                field_name=field,
                old_value=_format_value(old_val),
                new_value=_format_value(new_val),
                detected_at=now,
            )
            db.add(change)
            changes.append(change)

            logger.info(
                "jobs.temporal.change_detected",
                role_id=role.id,
                change_type=change_type,
                field=field,
                old_value=old_val,
                new_value=new_val,
            )

    # Check set fields (order doesn't matter)
    for field, change_type in TRACKED_SET_FIELDS.items():
        old_val = set(_extract_field(old_data, field) or [])
        new_val = set(_extract_field(new_data, field) or [])

        if old_val != new_val:
            change = RoleChange(
                role_id=role.id,
                scrape_run_id=scrape_run.id,
                change_type=change_type,
                field_name=field,
                old_value=_format_value(sorted(old_val)),
                new_value=_format_value(sorted(new_val)),
                detected_at=now,
            )
            db.add(change)
            changes.append(change)

            logger.info(
                "jobs.temporal.change_detected",
                role_id=role.id,
                change_type=change_type,
                field=field,
                added=sorted(new_val - old_val),
                removed=sorted(old_val - new_val),
            )

    return changes


async def mark_disappeared_roles(
    db: AsyncSession,
    scrape_run: RoleScrapeRun,
    seen_paraform_ids: set[str],
) -> int:
    """Mark roles not in current scrape as disappeared.

    Only marks roles that were previously ACTIVE.

    Args:
        db: Database session.
        scrape_run: Current scrape run.
        seen_paraform_ids: Set of paraform IDs seen in this scrape.

    Returns:
        Number of roles marked as disappeared.
    """
    now = datetime.now(UTC)

    # Find active roles not in the current scrape
    stmt = select(Role).where(Role.lifecycle_status == "ACTIVE")

    if seen_paraform_ids:
        stmt = stmt.where(Role.paraform_id.notin_(seen_paraform_ids))

    result = await db.execute(stmt)
    missing_roles = result.scalars().all()

    disappeared_count = 0
    for role in missing_roles:
        # Mark as disappeared
        role.lifecycle_status = "FILLED"  # Assume filled unless we know otherwise
        role.disappeared_at = now

        # Record the change
        change = RoleChange(
            role_id=role.id,
            scrape_run_id=scrape_run.id,
            change_type="DISAPPEARED",
            field_name="lifecycle_status",
            old_value="ACTIVE",
            new_value="FILLED",
            detected_at=now,
        )
        db.add(change)
        disappeared_count += 1

        logger.info(
            "jobs.temporal.role_disappeared",
            role_id=role.id,
            paraform_id=role.paraform_id,
            company=role.company_name,
            title=role.title,
        )

    return disappeared_count


async def mark_reappeared_role(
    db: AsyncSession,
    role: Role,
    scrape_run: RoleScrapeRun,
) -> RoleChange | None:
    """Mark a previously disappeared role as reappeared.

    Args:
        db: Database session.
        role: Role that reappeared.
        scrape_run: Current scrape run.

    Returns:
        Change record if role reappeared, None otherwise.
    """
    if role.lifecycle_status == "ACTIVE":
        return None  # Already active, no change

    now = datetime.now(UTC)
    old_status = role.lifecycle_status

    # Reactivate
    role.lifecycle_status = "ACTIVE"
    role.disappeared_at = None

    # Record the change
    change = RoleChange(
        role_id=role.id,
        scrape_run_id=scrape_run.id,
        change_type="REAPPEARED",
        field_name="lifecycle_status",
        old_value=old_status,
        new_value="ACTIVE",
        detected_at=now,
    )
    db.add(change)

    logger.info(
        "jobs.temporal.role_reappeared",
        role_id=role.id,
        paraform_id=role.paraform_id,
        previous_status=old_status,
    )

    return change


async def get_role_changes(
    db: AsyncSession,
    role_id: int | None = None,
    since: datetime | None = None,
    change_types: list[str] | None = None,
    limit: int = 100,
) -> list[RoleChange]:
    """Query role changes with optional filters.

    Args:
        db: Database session.
        role_id: Filter by specific role (optional).
        since: Only changes after this timestamp (optional).
        change_types: Filter by change types (optional).
        limit: Maximum results to return.

    Returns:
        List of changes matching filters.
    """
    stmt = select(RoleChange)

    if role_id is not None:
        stmt = stmt.where(RoleChange.role_id == role_id)

    if since is not None:
        stmt = stmt.where(RoleChange.detected_at > since)

    if change_types:
        stmt = stmt.where(RoleChange.change_type.in_(change_types))

    stmt = stmt.order_by(RoleChange.detected_at.desc()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_role_snapshots(
    db: AsyncSession,
    role_id: int,
    limit: int = 10,
) -> list[RoleSnapshot]:
    """Get snapshots for a role, most recent first.

    Args:
        db: Database session.
        role_id: Role ID.
        limit: Maximum snapshots to return.

    Returns:
        List of snapshots.
    """
    stmt = (
        select(RoleSnapshot)
        .where(RoleSnapshot.role_id == role_id)
        .order_by(RoleSnapshot.scraped_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
