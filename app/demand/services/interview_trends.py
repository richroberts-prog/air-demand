"""Interview trend calculation service.

Analyzes role changes to detect interview pipeline trends (surging, stalled, hired).
Used by both API responses and email digest generation.
"""

from app.core.logging import get_logger
from app.demand.models import Role, RoleChange

logger = get_logger(__name__)


def calculate_interview_trend(role: Role, changes: dict[int, list[RoleChange]]) -> str | None:
    """Calculate interview trend badge from role changes.

    Analyzes recent role changes to determine if:
    - "surging": Interview activity increased (🔥)
    - "stalled": Interviews dropped to 0 without hiring increase (⚠️)
    - "hired": Hiring count increased (✅)

    Args:
        role: Role to calculate trend for
        changes: Dict mapping role_id to list of RoleChange records

    Returns:
        "surging" if interviews increased
        "stalled" if interviews dropped to 0 with no hiring increase
        "hired" if hiring increased
        None if no significant changes

    Examples:
        >>> changes = {123: [RoleChange(change_type="INTERVIEW_INCREASE", ...)]}
        >>> calculate_interview_trend(role, changes)
        'surging'
    """
    role_changes = changes.get(role.id, [])
    if not role_changes:
        return None

    # Check for hiring increase (highest priority)
    for change in role_changes:
        if change.change_type == "HIRING_INCREASE":
            return "hired"

    # Check for interview changes
    for change in role_changes:
        if change.change_type == "INTERVIEW_INCREASE":
            return "surging"
        elif change.change_type == "INTERVIEW_DECREASE":
            # Only mark as stalled if interviews went to 0
            if change.new_value == "0":
                return "stalled"

    return None


def get_role_trends(roles: list[Role], changes: dict[int, list[RoleChange]]) -> dict[int, str]:
    """Calculate interview trends for multiple roles.

    Args:
        roles: List of roles to calculate trends for
        changes: Dict mapping role_id to list of RoleChange records

    Returns:
        Dict mapping role_id to trend ("surging", "stalled", "hired", or None)

    Examples:
        >>> trends = get_role_trends(roles, changes)
        >>> trends[123]
        'surging'
    """
    trends = {}
    for role in roles:
        trend = calculate_interview_trend(role, changes)
        if trend:
            trends[role.id] = trend

    return trends
