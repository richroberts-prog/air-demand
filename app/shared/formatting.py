"""Shared formatting utilities for demand-side codebase.

Provides consistent formatting across backend (digest, routes, schemas) and
frontend (dashboard components). All formats follow ADR-003 standards.

Formatting Standards:
- Salary: "225K" (upper bound only, thousands format, no $)
- Funding: "10.7M" (millions with M suffix)
- Date: "2024-12-09" (ISO format)
- Score: "85" (integer 0-100, from 0.0-1.0 float)
"""

import re
from datetime import UTC, datetime

from app.shared.constants import (
    FUNDING_STAGE_DISPLAY,
    INDUSTRY_DISPLAY,
    ROLE_TYPE_DISPLAY,
    SCORE_THRESHOLD_HIGH,
    SCORE_THRESHOLD_MEDIUM,
    ScoreTier,
)

# ====================
# Salary Formatting
# ====================


def format_salary(lower: int | None, upper: int | None) -> str:
    """Format salary to thousands (no suffix).

    Column headers should indicate units ("$K").

    Args:
        lower: Lower salary bound (ignored per ADR-003)
        upper: Upper salary bound

    Returns:
        Formatted salary (e.g., "225") or "—" if no data

    Examples:
        >>> format_salary(None, 225000)
        '225'
        >>> format_salary(None, None)
        '—'
    """
    if upper:
        thousands = upper // 1000
        return f"{thousands}"
    return "—"


# ====================
# Funding Formatting
# ====================


def format_funding_amount(amount_str: str | None) -> str:
    """Format funding amount to integer millions (no suffix, no decimals).

    Returns whole millions as integer string (e.g., "10", "70", "1500").
    Used for compact display in dashboard and email digest.

    Args:
        amount_str: Funding amount as string (e.g., "$10.7M", "10124987", "undisclosed")

    Returns:
        Integer millions (e.g., "10", "70") or "—" for undisclosed/missing

    Examples:
        >>> format_funding_amount("$10.7M")
        '10'
        >>> format_funding_amount("$70M")
        '70'
        >>> format_funding_amount("70000000")
        '70'
        >>> format_funding_amount("$1.5B")
        '1500'
        >>> format_funding_amount("undisclosed")
        '—'
        >>> format_funding_amount(None)
        '—'
    """
    if not amount_str:
        return "—"

    # Skip text values
    if amount_str.lower() in ["undisclosed", "unknown", "a lot", "n/a"]:
        return "—"

    def _format_millions(amount: float) -> str:
        """Format millions as integer (no decimals, no suffix)."""
        return str(int(round(amount)))

    # Already in millions format (e.g., "$10.7M", "231M")
    if re.search(r"[Mm]", amount_str):
        match = re.search(r"([\d.]+)", amount_str)
        if match:
            amount = float(match.group(1))
            return _format_millions(amount)

    # Already in billions format (e.g., "$1.5B")
    if re.search(r"[Bb]", amount_str):
        match = re.search(r"([\d.]+)", amount_str)
        if match:
            amount = float(match.group(1))
            # Convert billions to millions
            millions = amount * 1000
            return _format_millions(millions)

    # Raw dollar amount (pure digits)
    if amount_str.replace("$", "").replace(",", "").strip().replace(".", "").isdigit():
        try:
            amount = float(amount_str.replace("$", "").replace(",", "").strip())
            # Convert to millions
            millions = amount / 1_000_000
            return _format_millions(millions)
        except ValueError:
            return "—"

    return "—"


def parse_funding_amount(amount_str: str | None) -> float:
    """Parse funding amount string to USD value.

    For scoring calculations (not display).

    Args:
        amount_str: Funding amount string (e.g., "$16.25M", "100M", "$1.5B")

    Returns:
        Funding amount in USD, or 0.0 if unparseable

    Examples:
        >>> parse_funding_amount("$16.25M")
        16250000.0
        >>> parse_funding_amount("100M")
        100000000.0
        >>> parse_funding_amount("$1.5B")
        1500000000.0
    """
    if not amount_str:
        return 0.0

    # Clean the string
    cleaned = amount_str.replace("$", "").replace(",", "").strip()

    try:
        if "B" in cleaned.upper():
            num = float(cleaned.upper().replace("B", ""))
            return num * 1_000_000_000
        elif "M" in cleaned.upper():
            num = float(cleaned.upper().replace("M", ""))
            return num * 1_000_000
        elif "K" in cleaned.upper():
            num = float(cleaned.upper().replace("K", ""))
            return num * 1_000
        else:
            # Assume raw number
            return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0


# ====================
# Date Formatting
# ====================


def format_date_iso(dt: datetime | str | None) -> str:
    """Format date to ISO format.

    Per ADR-003: Use "YYYY-MM-DD" format (e.g., "2024-12-09").

    Args:
        dt: Datetime object or ISO string

    Returns:
        ISO formatted date or "—" if None

    Examples:
        >>> from datetime import datetime
        >>> format_date_iso(datetime(2024, 12, 9))
        '2024-12-09'
        >>> format_date_iso("2024-12-09T10:30:00Z")
        '2024-12-09'
        >>> format_date_iso(None)
        '—'
    """
    if not dt:
        return "—"

    try:
        if isinstance(dt, str):
            # Parse ISO string
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed.strftime("%Y-%m-%d")
        else:
            # Assume datetime object
            return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError, AttributeError):
        return "—"


def format_date_short(dt: datetime | str | None) -> str:
    """Format date to short format (MM-DD).

    For compact display in email digests.

    Args:
        dt: Datetime object or ISO string

    Returns:
        Short formatted date (MM-DD) or "—" if None

    Examples:
        >>> from datetime import datetime
        >>> format_date_short(datetime(2024, 12, 9))
        '12-09'
        >>> format_date_short("2024-12-09T10:30:00Z")
        '12-09'
        >>> format_date_short(None)
        '—'
    """
    if not dt:
        return "—"

    try:
        if isinstance(dt, str):
            # Parse ISO string
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed.strftime("%m-%d")
        else:
            # Assume datetime object
            return dt.strftime("%m-%d")
    except (ValueError, TypeError, AttributeError):
        return "—"


def format_manager_active(dt: datetime | str | None) -> str:
    """Format manager last active as relative time.

    Shows how long ago the manager was last active:
    - Today
    - 1d (1 day ago)
    - 5d (5 days ago)
    - 2w (2 weeks ago)
    - 3mo (3 months ago)

    Args:
        dt: Datetime object or ISO string of when manager was last active

    Returns:
        Relative time string or "—" if None

    Examples:
        >>> from datetime import datetime, timezone, timedelta
        >>> now = datetime.now(timezone.utc)
        >>> format_manager_active(now)
        'Today'
        >>> format_manager_active(now - timedelta(days=1))
        '1d'
        >>> format_manager_active(now - timedelta(days=5))
        '5d'
        >>> format_manager_active(now - timedelta(days=14))
        '2w'
        >>> format_manager_active(now - timedelta(days=60))
        '2mo'
        >>> format_manager_active(None)
        '—'
    """
    if not dt:
        return "—"

    try:
        if isinstance(dt, str):
            # Parse ISO string
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        else:
            parsed = dt

        # Ensure timezone aware
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        diff_seconds = (now - parsed).total_seconds()
        diff_days = int(diff_seconds / (60 * 60 * 24))

        if diff_days == 0:
            return "Today"
        if diff_days == 1:
            return "1d"
        if diff_days < 7:
            return f"{diff_days}d"
        if diff_days < 30:
            weeks = diff_days // 7
            return f"{weeks}w"

        months = diff_days // 30
        return f"{months}mo"

    except (ValueError, TypeError, AttributeError):
        return "—"


# ====================
# Score Formatting
# ====================


def format_score(score: float | None) -> str:
    """Format score as integer 0-100.

    Per ADR-003: Convert 0.0-1.0 float to 0-100 integer (e.g., 0.85 → "85").

    Args:
        score: Score from 0.0 to 1.0

    Returns:
        Integer score 0-100 or "—" if None

    Examples:
        >>> format_score(0.85)
        '85'
        >>> format_score(0.923)
        '92'
        >>> format_score(None)
        '—'
    """
    if score is None:
        return "—"
    score_int = int(score * 100)
    return str(score_int)


def get_score_tier(score: float | None) -> ScoreTier:
    """Get the tier for a given score.

    Per ADR-003: high ≥0.85, medium ≥0.70, low <0.70

    Args:
        score: Score from 0.0 to 1.0

    Returns:
        "high", "medium", "low", or "none"

    Examples:
        >>> get_score_tier(0.90)
        'high'
        >>> get_score_tier(0.75)
        'medium'
        >>> get_score_tier(0.60)
        'low'
        >>> get_score_tier(None)
        'none'
    """
    if score is None:
        return "none"
    if score >= SCORE_THRESHOLD_HIGH:
        return "high"
    elif score >= SCORE_THRESHOLD_MEDIUM:
        return "medium"
    else:
        return "low"


# ====================
# Funding Stage Formatting
# ====================


def format_funding_stage(stage: str | None) -> str:
    """Format funding stage to abbreviated form.

    Args:
        stage: Funding stage enum (e.g., "SERIES_A", "SEED")

    Returns:
        Abbreviated stage (e.g., "A", "Seed") or "—"

    Examples:
        >>> format_funding_stage("SERIES_A")
        'A'
        >>> format_funding_stage("SEED")
        'Seed'
        >>> format_funding_stage(None)
        '—'
    """
    if not stage:
        return "—"

    stage_upper = stage.upper()
    return FUNDING_STAGE_DISPLAY.get(stage_upper, stage_upper[0] if stage_upper else "—")


# ====================
# Industry Formatting
# ====================


def format_industry(industries: list[str]) -> str:
    """Format industry list to display name.

    Prioritizes non-generic industries (filters out "software_development", "ai").

    Args:
        industries: List of industry identifiers

    Returns:
        Display name for primary industry or "—"

    Examples:
        >>> format_industry(["software_development", "fintech"])
        'Fintech'
        >>> format_industry(["ai", "healthcare"])
        'Healthcare'
        >>> format_industry([])
        '—'
    """
    if not industries:
        return "—"

    # Filter out generic industries
    non_generic = [i for i in industries if i not in ["software_development", "ai"]]
    primary = non_generic[0] if non_generic else industries[0]

    return INDUSTRY_DISPLAY.get(primary, primary.replace("_", " ").title()[:15])


# ====================
# Role Type Formatting
# ====================


def format_role_type(role_types: list[str]) -> str:
    """Format role type list to display name.

    Args:
        role_types: List of role type identifiers

    Returns:
        Display name for primary role type or "—"

    Examples:
        >>> format_role_type(["backend_engineer"])
        'Backend'
        >>> format_role_type(["full_stack_engineer"])
        'Full Stack'
        >>> format_role_type([])
        '—'
    """
    if not role_types:
        return "—"

    primary = role_types[0]
    return ROLE_TYPE_DISPLAY.get(primary, primary.replace("_", " ").title()[:18])


# ====================
# Location Formatting
# ====================


def format_location(
    locations: list[str],
    workplace_type: str | None = None,
    max_locations: int = 2,
) -> str:
    """Format location to display city names.

    Shows actual location names using LOCATION_DISPLAY mapping.
    For Remote roles with no specific locations, returns "Remote".

    Args:
        locations: List of location identifiers (e.g., ["new_york", "san_francisco"])
        workplace_type: Workplace type (e.g., "Remote", "Hybrid", "On-site")
        max_locations: Maximum number of locations to show (default: 2)

    Returns:
        Location string (e.g., "NYC", "SF", "Remote")

    Examples:
        >>> format_location(["new_york"], "On-site")
        'NYC'
        >>> format_location(["san_francisco", "new_york"], "Hybrid")
        'SF'
        >>> format_location([], "Remote")
        'Remote'
        >>> format_location(["new_york"], None)
        'NYC'
    """
    from app.shared.constants import LOCATION_DISPLAY

    # If Remote with no specific locations, show "Remote"
    if workplace_type == "Remote" and not locations:
        return "Remote"

    # Show location names using LOCATION_DISPLAY mapping
    if locations:
        # Get the first location (primary)
        primary_location = locations[0]
        # Fallback: format and limit to 4 chars max for compact display
        fallback = primary_location.replace("_", " ").title()[:4]
        return LOCATION_DISPLAY.get(primary_location, fallback)

    # Fallback: if no locations but has workplace type, show "Remote" or "—"
    if workplace_type == "Remote":
        return "Remote"

    return "—"


# ====================
# Utility Formatters
# ====================


def format_hiring_count(count: int | None) -> str:
    """Format total hiring count.

    Shows total positions the company wants to fill (not remaining).
    Use format_remaining_positions() for remaining open positions.

    Args:
        count: Total number of positions

    Returns:
        Total positions as string, "1" if None, "0" if zero

    Examples:
        >>> format_hiring_count(5)
        '5'
        >>> format_hiring_count(100)
        '100'
        >>> format_hiring_count(None)
        '1'
        >>> format_hiring_count(0)
        '0'
    """
    # None means unknown, default to 1
    if count is None:
        return "1"

    return str(count)


def format_remaining_positions(count: int | None, total_hired: int | None = None) -> str:
    """Format remaining open positions after subtracting hires.

    Shows how many positions are still available (count - total_hired).
    This indicates urgency and available slots.

    Args:
        count: Total number of positions
        total_hired: Number already hired (optional)

    Returns:
        Remaining positions as string, or same as count if no hires

    Examples:
        >>> format_remaining_positions(5, 0)
        '5'
        >>> format_remaining_positions(10, 3)
        '7'
        >>> format_remaining_positions(100, 17)
        '83'
        >>> format_remaining_positions(None, 0)
        '1'
        >>> format_remaining_positions(0, 0)
        '0'
    """
    # None means unknown, default to 1
    if count is None:
        return "1"

    # Zero means explicitly no positions available
    if count == 0:
        return "0"

    # Calculate remaining open positions
    if total_hired and total_hired > 0:
        remaining = max(count - total_hired, 0)
        return str(remaining)

    return str(count)


def format_percent_fee(fee: float | None) -> str:
    """Format recruiter fee percentage (no suffix).

    Column headers should indicate units ("Fee %").

    Args:
        fee: Fee percentage (e.g., 15.5)

    Returns:
        Formatted percentage (e.g., "15.5") or "—"

    Examples:
        >>> format_percent_fee(15.5)
        '15.5'
        >>> format_percent_fee(None)
        '—'
    """
    if fee is None:
        return "—"
    return f"{fee:.1f}"


# ====================
# Disqualification Categorization
# ====================


def get_disqualification_category(reasons: list[str]) -> str:
    """Get primary disqualification category for compact digest display.

    Maps verbose disqualification reasons to high-level category codes.
    When multiple categories apply, returns the highest priority.

    Priority order (highest to lowest):
    1. COMP - Compensation issues (salary/fee)
    2. TYPE - Role type (not core engineering)
    3. LOC - Location (not NYC/Remote)
    4. HIRING - No positions available
    5. STAGE - Funding stage mismatch
    6. YOE - Experience requirements
    7. EQUITY - Equity structure issues

    Args:
        reasons: List of disqualification reason strings

    Returns:
        Category code: COMP, TYPE, LOC, HIRING, STAGE, YOE, EQUITY, or MULTI

    Examples:
        >>> get_disqualification_category(["Commission below 14%: 12.5%"])
        'COMP'
        >>> get_disqualification_category([
        ...     "Location not NYC/Remote: ['sf']",
        ...     "Commission below 14%: 13%"
        ... ])
        'COMP'
    """
    if not reasons:
        return ""

    # Priority order (highest first)
    priority = ["COMP", "TYPE", "LOC", "HIRING", "STAGE", "YOE", "EQUITY"]
    categories = set()

    for reason in reasons:
        reason_lower = reason.lower()

        # Compensation issues (highest priority)
        if any(x in reason_lower for x in ["commission", "salary"]):
            categories.add("COMP")

        # Role type issues
        elif any(
            x in reason_lower
            for x in ["not core engineering", "non-technical", "not accepting recruiters"]
        ):
            categories.add("TYPE")

        # Location issues
        elif any(x in reason_lower for x in ["location not", "wrong location"]):
            categories.add("LOC")

        # Hiring issues
        elif "no positions available" in reason_lower or "hiring_count=0" in reason_lower:
            categories.add("HIRING")

        # Stage issues
        elif any(x in reason_lower for x in ["pre-seed", "stage mismatch"]):
            categories.add("STAGE")

        # YOE issues
        elif "yoe" in reason_lower or "experience requirement" in reason_lower:
            categories.add("YOE")

        # Equity issues
        elif "equity" in reason_lower:
            categories.add("EQUITY")

    if not categories:
        return "MULTI"  # Couldn't categorize

    if len(categories) == 1:
        return list(categories)[0]

    # Multiple categories - return highest priority
    for cat in priority:
        if cat in categories:
            return cat

    return "MULTI"
