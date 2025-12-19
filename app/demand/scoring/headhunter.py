"""Headhunter scoring for role evaluation.

Calculates how attractive a role is to recruit for, based on:
- Placement probability (35%)
- Commission value (30%)
- Competition level (20%)
- Candidate fit (15%)
"""

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.shared.constants import SUPPORTED_LOCATIONS

logger = get_logger(__name__)


# ====================
# Scoring Result
# ====================


@dataclass
class ScoringResult:
    """Result of a scoring calculation with breakdown."""

    score: float  # 0.00-1.00
    breakdown: dict[str, float] = field(default_factory=lambda: {})
    signals: list[str] = field(default_factory=lambda: [])


# ====================
# Helper Functions
# ====================


def normalize(
    value: float | int | None,
    min_val: float,
    max_val: float,
    inverse: bool = False,
) -> float:
    """Normalize a value to 0.0-1.0 range.

    Args:
        value: The value to normalize
        min_val: Minimum value (maps to 0.0)
        max_val: Maximum value (maps to 1.0)
        inverse: If True, flip the scale (high value = low score)

    Returns:
        Normalized value clamped to [0.0, 1.0]
    """
    if value is None:
        return 0.5  # Default for missing data

    if max_val == min_val:
        return 0.5

    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0.0, min(1.0, normalized))

    if inverse:
        normalized = 1.0 - normalized

    return normalized


# ====================
# Compensation Scoring
# ====================


def score_compensation(
    salary_upper: int | None,
    percent_fee: float | None,
) -> tuple[float, float, list[str]]:
    """Score compensation attractiveness.

    Args:
        salary_upper: Upper salary bound
        percent_fee: Recruiter commission percentage

    Returns:
        Tuple of (engineer_score, headhunter_score, signals)
    """
    signals: list[str] = []

    # Salary score for engineers (they expect $250k+)
    if salary_upper:
        if salary_upper >= 300000:
            eng_salary_score = 1.0
            signals.append(f"${salary_upper:,} salary (excellent)")
        elif salary_upper >= 250000:
            eng_salary_score = 0.85
            signals.append(f"${salary_upper:,} salary (strong)")
        elif salary_upper >= 200000:
            eng_salary_score = 0.6
        else:
            eng_salary_score = 0.4
    else:
        eng_salary_score = 0.3

    # Fee score for headhunters
    fee = percent_fee or 15.0
    if fee >= 18:
        hh_fee_score = 1.0
        signals.append(f"{fee:.1f}% fee (excellent)")
    elif fee >= 16:
        hh_fee_score = 0.8
        signals.append(f"{fee:.1f}% fee")
    elif fee >= 14:
        hh_fee_score = 0.5
    else:
        hh_fee_score = 0.3

    # Commission value = fee * salary
    salary = salary_upper or 200000
    expected_commission = salary * (fee / 100)
    if expected_commission >= 40000:
        signals.append(f"${expected_commission:,.0f} expected commission")

    return eng_salary_score, hh_fee_score, signals


# ====================
# Process Quality Scoring
# ====================


def score_process_quality(
    manager_rating: float | None,
    responsiveness_days: float | None,
    interview_stages: int | None,
    highlights: list[str] | None,
) -> tuple[float, float, list[str]]:
    """Score hiring process quality.

    Args:
        manager_rating: Manager rating (1-5)
        responsiveness_days: Days to respond
        interview_stages: Number of interview rounds
        highlights: Role highlight badges

    Returns:
        Tuple of (engineer_score, headhunter_score, signals)
    """
    signals: list[str] = []
    highlights_set = set(highlights or [])

    # Manager rating (critical for headhunters)
    rating = manager_rating or 4.0
    rating_score = normalize(rating, 3.0, 5.0)
    if rating >= 4.5:
        signals.append(f"{rating:.1f}/5 manager rating")

    # Responsiveness (both care, but headhunters more)
    resp = responsiveness_days if responsiveness_days is not None else 2.0
    resp_score = 1.0 - normalize(resp, 0, 5.0)  # Lower is better
    if resp < 1.0:
        signals.append("<1 day response time")
    elif resp < 2.0:
        signals.append(f"Fast responses ({resp:.1f} days)")

    # Interview stages (engineers hate long processes)
    stages = interview_stages or 5
    if stages <= 4:
        stage_score = 1.0
        signals.append(f"{stages} interview rounds (fast process)")
    elif stages <= 6:
        stage_score = 0.7
    else:
        stage_score = 0.4

    # Badges
    badge_score = 0.0
    if "NO_FINAL_ROUNDS" in highlights_set:
        badge_score += 0.3
        signals.append("No final rounds required")
    if "TRUSTED_CLIENT" in highlights_set:
        badge_score += 0.25
        signals.append("Trusted client")
    if "RESPONSIVE" in highlights_set:
        badge_score += 0.2
    if "HIRING_MULTIPLE" in highlights_set:
        badge_score += 0.15
        signals.append("Hiring multiple")

    # Engineer process score: stages (40%) + resp (30%) + badges (30%)
    eng_score = (stage_score * 0.4) + (resp_score * 0.3) + (min(1.0, badge_score) * 0.3)

    # Headhunter score: rating (40%) + resp (30%) + badges (30%)
    hh_score = (rating_score * 0.4) + (resp_score * 0.3) + (min(1.0, badge_score) * 0.3)

    return eng_score, hh_score, signals


# ====================
# Competition Scoring
# ====================


def score_competition(
    approved_recruiters: int | None,
    total_interviewing: int | None,
    total_hired: int | None,
) -> tuple[float, list[str]]:
    """Score competition level (headhunter perspective).

    Args:
        approved_recruiters: Number of approved recruiters
        total_interviewing: Candidates currently interviewing
        total_hired: Total placements made

    Returns:
        Tuple of (score 0.0-1.0, signals)
    """
    signals: list[str] = []

    # Recruiter competition (lower is better for us)
    recruiters = approved_recruiters or 0
    if recruiters == 0:
        recruiter_score = 1.0
        signals.append("Blue ocean (0 approved recruiters)")
    elif recruiters <= 2:
        recruiter_score = 0.8
    elif recruiters <= 5:
        recruiter_score = 0.6
    elif recruiters <= 10:
        recruiter_score = 0.4
    else:
        recruiter_score = 0.2
        signals.append(f"Crowded ({recruiters} recruiters)")

    # Track record (higher is better - proves they hire)
    hired = total_hired or 0
    if hired >= 2:
        track_score = 1.0
        signals.append(f"{hired} placements made (proven buyer)")
    elif hired >= 1:
        track_score = 0.8
        signals.append(f"{hired} placement(s) made")
    else:
        track_score = 0.5

    # Pipeline activity (moderate is good)
    interviewing = total_interviewing or 0
    if 1 <= interviewing <= 5:
        pipeline_score = 1.0
        signals.append(f"{interviewing} candidates interviewing")
    elif interviewing > 10:
        pipeline_score = 0.6  # Maybe saturated
    else:
        pipeline_score = 0.7

    # Combine: recruiter (50%) + track (30%) + pipeline (20%)
    combined = (recruiter_score * 0.5) + (track_score * 0.3) + (pipeline_score * 0.2)

    return combined, signals


# ====================
# Main Headhunter Scoring
# ====================


def calculate_headhunter_score(role_data: dict[str, Any]) -> ScoringResult:
    """Calculate headhunter attractiveness score.

    What we optimize for:
    1. Placement probability (35%) - will we actually close this?
    2. Commission value (30%) - is it worth our time?
    3. Competition level (20%) - are we fighting 50 other recruiters?
    4. Candidate fit (15%) - do we have candidates who match?

    Args:
        role_data: Raw role data dict

    Returns:
        ScoringResult with score, breakdown, and signals
    """
    all_signals: list[str] = []
    breakdown: dict[str, float] = {}

    # Extract data
    salary_upper = role_data.get("salaryUpperBound")
    percent_fee = role_data.get("percent_fee")
    manager_rating = role_data.get("manager_rating")
    resp_days = role_data.get("responsiveness_days")
    interview_stages = role_data.get("interview_stages")
    highlights = role_data.get("role_metadata", {}).get("highlights", [])
    approved_recruiters = role_data.get("approved_recruiters_count")
    total_interviewing = role_data.get("total_interviewing")
    total_hired = role_data.get("total_hired")
    hiring_count = role_data.get("hiring_count", 1) or 1
    role_types = role_data.get("role_types", [])
    locations = role_data.get("locations", [])
    workplace_type = role_data.get("workplace_type")

    # 1. Placement probability (35%)
    _, hh_process, process_signals = score_process_quality(
        manager_rating, resp_days, interview_stages, highlights
    )
    breakdown["placement_probability"] = round(hh_process, 3)
    all_signals.extend(process_signals[:2])

    # 2. Commission value (30%)
    _, hh_fee_score, comp_signals = score_compensation(salary_upper, percent_fee)

    # Volume bonus
    volume_score = min(1.0, hiring_count / 3)
    if hiring_count >= 3:
        all_signals.append(f"Hiring {hiring_count}+ (multiple commissions)")

    # Bonus opportunity
    has_bonus = "ROLE_BONUS" in (highlights or [])
    bonus_score = 1.0 if has_bonus else 0.5
    if has_bonus:
        all_signals.append("Role bonus available")

    commission_score = (hh_fee_score * 0.5) + (volume_score * 0.3) + (bonus_score * 0.2)
    breakdown["commission_value"] = round(commission_score, 3)
    all_signals.extend(comp_signals[:1])

    # 3. Competition level (20%)
    competition_score, comp_signals = score_competition(
        approved_recruiters, total_interviewing, total_hired
    )
    breakdown["competition"] = round(competition_score, 3)
    all_signals.extend(comp_signals[:2])

    # 4. Candidate fit (15%)
    # Common role types we can source for
    common_types = {"full_stack_engineer", "backend_engineer", "frontend_engineer", "data_engineer"}
    role_types_lower = {rt.lower() for rt in role_types}
    type_score = 1.0 if (role_types_lower & common_types) else 0.6

    # Location fit - use SUPPORTED_LOCATIONS
    locations_lower = [loc.lower() for loc in locations]
    is_supported = any(loc in SUPPORTED_LOCATIONS for loc in locations_lower)
    is_remote = (workplace_type or "").lower() == "remote"
    location_score = 1.0 if (is_supported or is_remote) else 0.5

    candidate_fit = (type_score * 0.5) + (location_score * 0.5)
    breakdown["candidate_fit"] = round(candidate_fit, 3)

    # Final weighted score
    final_score = (
        breakdown["placement_probability"] * 0.35
        + breakdown["commission_value"] * 0.30
        + breakdown["competition"] * 0.20
        + breakdown["candidate_fit"] * 0.15
    )

    return ScoringResult(
        score=round(final_score, 2),
        breakdown=breakdown,
        signals=all_signals[:5],
    )
