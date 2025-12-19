"""Role qualification logic for v0.1.

Determines whether a role matches our archetype based on:
1. Hard filters (must pass all)
2. Quality signals (for tiering)

Tiers:
- QUALIFIED: Passes hard filters + 3+ quality signals
- MAYBE: Passes hard filters + 1-2 quality signals
- LOCATION_UNCERTAIN: Passes all filters except location (needs enrichment) - NOT shown in dashboard
- SKIP: Fails any hard filter OR 0 quality signals
"""

from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.shared.constants import SUPPORTED_LOCATIONS, TIER_1_INVESTORS

# Tier constants
TIER_QUALIFIED = "QUALIFIED"
TIER_MAYBE = "MAYBE"
TIER_LOCATION_UNCERTAIN = "LOCATION_UNCERTAIN"  # Needs enrichment to resolve location
TIER_SKIP = "SKIP"

logger = get_logger(__name__)


@dataclass
class QualificationResult:
    """Result of role qualification check."""

    is_qualified: bool
    tier: str  # QUALIFIED, MAYBE, SKIP
    reasons: list[str]  # Why it qualified (quality signals met)
    disqualifications: list[str]  # Why it was disqualified (hard filters failed)


# Core engineering role types - roles must have at least ONE of these
# These are the primary qualifying types for our archetype
CORE_ENGINEERING_ROLE_TYPES = {
    "backend_engineer",
    "full_stack_engineer",
    "embedded_firmware_engineer",
    "electrical_engineer",
    "mechanical_engineer",
    "forward_deployed_engineer_solutions_support",
}

# Secondary engineering types - can qualify ONLY if paired with a core type
# These alone don't meet our archetype but are acceptable as secondary skills
SECONDARY_ENGINEERING_ROLE_TYPES = {
    "frontend_engineer",
    "infrastructure_devops_sre",
    "data_engineer",
    "security_engineer",
}

# All valid engineering types (for reference)
ENGINEERING_ROLE_TYPES = CORE_ENGINEERING_ROLE_TYPES | SECONDARY_ENGINEERING_ROLE_TYPES

# Mobile role types to explicitly exclude
MOBILE_ROLE_TYPES = {
    "mobile_engineer",
    "ios_engineer",
    "android_engineer",
}

# NYC_METRO_LOCATIONS is now imported from app.shared.constants as part of SUPPORTED_LOCATIONS


def _check_hard_filters(data: dict[str, Any]) -> tuple[bool, list[str], bool]:
    """Check hard filters that must all pass.

    Returns:
        Tuple of (passes_all, list of failed filter reasons, location_uncertain).
        location_uncertain is True when location fails but API had empty locations
        (suggesting location might be extractable from HTML).
    """
    failures: list[str] = []
    location_uncertain = False

    # 1. Status must be ACTIVE
    status = data.get("status", "").upper()
    if status != "ACTIVE":
        failures.append(f"Status is {status}, not ACTIVE")

    # 2. Must be accepting recruiters
    not_accepting = data.get("not_accepting_recruiters", False)
    if not_accepting:
        failures.append("Not accepting recruiters")

    # 3. Location: Supported metros OR US Remote OR check enrichment fallback
    # Three ways to qualify:
    # 1. API locations contains NYC or London
    # 2. workplace_type="remote" (US Remote, REGARDLESS of locations array)
    #    - Example: workplace_type="remote" + locations=["san_francisco"] qualifies
    #    - Assumption: "remote" means work-from-anywhere US remote
    # 3. LLM extracted NYC/London/remote with high confidence (fallback for empty locations)
    locations = data.get("locations", [])
    workplace_type = (data.get("workplace_type") or "").lower()
    is_remote = workplace_type == "remote"
    is_supported_api = any(
        loc.lower() in SUPPORTED_LOCATIONS for loc in locations if isinstance(loc, str)
    )

    # Check enrichment for extracted location (high confidence only)
    extracted_location = None
    location_confidence = None
    if "_enrichment" in data:
        extracted_data = data["_enrichment"].get("extracted_data", {})
        extracted_location = extracted_data.get("extracted_location")
        location_confidence = extracted_data.get("location_confidence")

    # High confidence extraction can qualify
    is_supported_extracted = False
    if extracted_location and location_confidence == "high":
        loc_lower = extracted_location.lower()
        is_supported_extracted = loc_lower in SUPPORTED_LOCATIONS or loc_lower == "remote"

    # Pass if: remote OR API locations supported OR high-confidence extraction supported
    location_passes = is_remote or is_supported_api or is_supported_extracted

    # Flag for location uncertainty (empty API locations, might be in HTML)
    if not location_passes and not locations:
        location_uncertain = True

    if not location_passes:
        failures.append(
            f"Location not supported: {locations or 'empty'}, {workplace_type}, "
            f"extracted: {extracted_location} ({location_confidence})"
        )

    # 4. Must have at least one CORE engineering role type
    # Secondary types (frontend, infra) are allowed but only alongside core types
    role_types = data.get("role_types", [])
    has_core_type = any(
        rt.lower() in CORE_ENGINEERING_ROLE_TYPES for rt in role_types if isinstance(rt, str)
    )

    if not has_core_type:
        # Check if they have ONLY secondary types
        has_secondary_only = any(
            rt.lower() in SECONDARY_ENGINEERING_ROLE_TYPES
            for rt in role_types
            if isinstance(rt, str)
        )
        if has_secondary_only:
            failures.append(f"Only secondary engineering types (frontend/infra): {role_types}")
        else:
            failures.append(f"Not core engineering role: {role_types}")

    # 5. Must NOT be a mobile role (explicit exclusion)
    is_mobile = any(rt.lower() in MOBILE_ROLE_TYPES for rt in role_types if isinstance(rt, str))
    if is_mobile:
        failures.append(f"Mobile role excluded: {role_types}")

    # 6. Salary upper bound must be >= $200k
    salary_upper = data.get("salaryUpperBound")
    if salary_upper is None or salary_upper < 200000:
        failures.append(f"Salary upper bound ${salary_upper or 0:,} < $200,000")

    # 7. Commission must be >= 14%
    percent_fee = data.get("percent_fee", 0) or 0
    if percent_fee < 14:
        failures.append(f"Commission {percent_fee}% < 14%")

    passes = len(failures) == 0
    return passes, failures, location_uncertain


def _count_quality_signals(data: dict[str, Any]) -> tuple[int, list[str]]:
    """Count quality signals met.

    Returns:
        Tuple of (signal_count, list of signal descriptions).
    """
    signals: list[str] = []

    # 1. Has tier-1 investors
    investors = data.get("investors", [])
    if investors:
        investor_lower = [i.lower() for i in investors if isinstance(i, str)]
        tier1_found = [i for i in investor_lower if any(t1 in i for t1 in TIER_1_INVESTORS)]
        if tier1_found:
            signals.append(f"Tier-1 investors: {', '.join(investors[:3])}")

    # 2. Well-funded (> $5M)
    company = data.get("company", {})
    funding_str = company.get("fundingAmount", "")
    if funding_str:
        # Parse "$16.25M" -> 16.25
        try:
            amount = funding_str.replace("$", "").replace(",", "")
            if "M" in amount:
                amount_num = float(amount.replace("M", ""))
                if amount_num > 5:
                    signals.append(f"Well-funded: {funding_str}")
            elif "B" in amount:
                signals.append(f"Well-funded: {funding_str}")
        except (ValueError, AttributeError):
            pass

    # 3. Good funding stage (Seed+)
    company_meta = company.get("company_metadata", {})
    funding_round = company_meta.get("last_funding_round", "")
    good_stages = {"SEED", "SERIES_A", "SERIES_B", "SERIES_C", "SERIES_D", "SERIES_E"}
    if funding_round and funding_round.upper() in good_stages:
        signals.append(f"Funding stage: {funding_round}")

    # 4. Company size 10-500 (sweet spot)
    company_size = company.get("size") or data.get("team_size")
    if company_size and 10 <= company_size <= 500:
        signals.append(f"Company size: {company_size} (sweet spot)")

    # 5. Good manager rating (>= 4 stars)
    manager_rating = data.get("manager_rating")
    if manager_rating and manager_rating >= 4:
        signals.append(f"Manager rating: {manager_rating}/5 stars")

    # 6. Responsive manager (< 3 days)
    responsiveness = data.get("responsiveness_days")
    if responsiveness is not None and responsiveness < 3:
        signals.append(f"Responsive manager: {responsiveness:.1f} days")

    # 7. Fast process (<= 6 interview stages)
    interview_stages = data.get("interview_stages")
    if interview_stages and interview_stages <= 6:
        signals.append(f"Fast process: {interview_stages} stages")

    # 8. Has highlights/badges
    role_meta = data.get("role_metadata", {})
    highlights = role_meta.get("highlights", [])
    if highlights:
        signals.append(f"Badges: {', '.join(highlights)}")

    return len(signals), signals


def qualify_role(data: dict[str, Any]) -> QualificationResult:
    """Determine if a role qualifies based on hard filters and quality signals.

    Args:
        data: Raw tRPC response for a single role.

    Returns:
        QualificationResult with tier, reasons, and disqualifications.
    """
    # Check hard filters
    passes_hard, failures, location_uncertain = _check_hard_filters(data)

    if not passes_hard:
        # Special case: ONLY location failed AND no API locations
        # Mark for enrichment (hidden from dashboard until resolved)
        if len(failures) == 1 and "Location not supported" in failures[0] and location_uncertain:
            return QualificationResult(
                is_qualified=False,  # Not qualified yet
                tier=TIER_LOCATION_UNCERTAIN,
                reasons=[],
                disqualifications=failures,
            )

        # Otherwise, hard skip
        return QualificationResult(
            is_qualified=False,
            tier=TIER_SKIP,
            reasons=[],
            disqualifications=failures,
        )

    # Count quality signals
    signal_count, signals = _count_quality_signals(data)

    # Determine tier
    if signal_count >= 3:
        tier = TIER_QUALIFIED
        is_qualified = True
    elif signal_count >= 1:
        tier = TIER_MAYBE
        is_qualified = True  # Still show MAYBE roles
    else:
        tier = TIER_SKIP
        is_qualified = False

    return QualificationResult(
        is_qualified=is_qualified,
        tier=tier,
        reasons=signals,
        disqualifications=[],
    )
