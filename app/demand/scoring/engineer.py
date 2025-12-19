"""Engineer scoring for role evaluation.

Calculates how attractive a role is to a top 1% engineer, based on:
- Compensation (30%)
- Company quality (25%)
- Role impact (20%)
- Process respect (15%)
- Tech modernity (10%)
"""

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.shared.constants import TIER_1_INVESTORS, TIER_2_INVESTORS
from app.shared.formatting import parse_funding_amount

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
# Investor Scoring
# ====================


def score_investors(investors: list[str]) -> tuple[float, int, list[str]]:
    """Score investor quality.

    Args:
        investors: List of investor names

    Returns:
        Tuple of (score 0.0-1.0, tier1_count, signal strings)
    """
    if not investors:
        return 0.3, 0, []  # No investors = below average

    signals: list[str] = []
    tier1_count = 0
    tier2_count = 0

    for inv in investors:
        inv_lower = inv.lower()

        # Check tier 1
        if any(t1 in inv_lower for t1 in TIER_1_INVESTORS):
            tier1_count += 1
            signals.append(f"Tier-1 VC: {inv}")

        # Check tier 2
        elif any(t2 in inv_lower for t2 in TIER_2_INVESTORS):
            tier2_count += 1
            if len(signals) < 3:  # Limit signals
                signals.append(f"Tier-2 VC: {inv}")

    # Calculate score: tier1 = 0.3 each (max 0.9), tier2 = 0.15 each
    score = min(1.0, tier1_count * 0.30 + tier2_count * 0.15)

    return score, tier1_count, signals


# ====================
# Funding Scoring
# ====================


def score_funding(amount: str | None, stage: str | None) -> tuple[float, list[str]]:
    """Score funding amount and stage.

    Args:
        amount: Funding amount string (e.g., "$17.3M")
        stage: Funding stage (e.g., "SERIES_A")

    Returns:
        Tuple of (score 0.0-1.0, signal strings)
    """
    signals: list[str] = []

    # Parse funding amount
    funding_usd = parse_funding_amount(amount)

    # Amount score (logarithmic - diminishing returns above $50M)
    if funding_usd >= 100_000_000:
        amount_score = 1.0
        signals.append(f"${funding_usd / 1_000_000:.0f}M raised (well-funded)")
    elif funding_usd >= 30_000_000:
        amount_score = 0.85
        signals.append(f"${funding_usd / 1_000_000:.0f}M raised")
    elif funding_usd >= 10_000_000:
        amount_score = 0.7
        signals.append(f"${funding_usd / 1_000_000:.1f}M raised")
    elif funding_usd >= 5_000_000:
        amount_score = 0.55
    elif funding_usd > 0:
        amount_score = 0.4
    else:
        amount_score = 0.3  # Unknown funding

    # Stage score
    stage_scores: dict[str, float] = {
        "SEED": 0.6,
        "PRE_SEED": 0.5,
        "SERIES_A": 1.0,  # Sweet spot
        "SERIES_B": 0.95,
        "SERIES_C": 0.85,
        "SERIES_D": 0.75,
        "SERIES_D_PLUS": 0.7,
        "SERIES_E": 0.65,
        "POST_IPO_EQUITY": 0.5,
    }
    stage_normalized = (stage or "").upper().replace(" ", "_")
    stage_score = stage_scores.get(stage_normalized, 0.5)

    if stage and stage_score >= 0.8:
        signals.append(f"Funding stage: {stage.replace('_', ' ').title()}")

    # Combine: 60% amount, 40% stage
    combined = (amount_score * 0.6) + (stage_score * 0.4)

    return combined, signals


# ====================
# Main Engineer Scoring
# ====================


def calculate_engineer_score(role_data: dict[str, Any]) -> ScoringResult:
    """Calculate engineer attractiveness score.

    What a top 1% engineer optimizes for:
    1. Compensation (30%) - they're in demand, expect $250k+
    2. Company quality (25%) - will this equity be worth something?
    3. Role impact (20%) - can I build something meaningful?
    4. Process respect (15%) - don't waste my time
    5. Tech modernity (10%) - modern stack + hot industry

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
    investors = role_data.get("investors", [])
    company = role_data.get("company", {})
    funding_amount = company.get("fundingAmount")
    funding_stage = company.get("company_metadata", {}).get("last_funding_round")
    company_size = company.get("size")
    manager_rating = role_data.get("manager_rating")
    resp_days = role_data.get("responsiveness_days")
    interview_stages = role_data.get("interview_stages")
    highlights = role_data.get("role_metadata", {}).get("highlights", [])
    tech_stack = role_data.get("tech_stack", [])
    industries = company.get("industries", [])
    title = role_data.get("name", "")

    # 1. Compensation (30%)
    eng_comp_score, _, comp_signals = score_compensation(salary_upper, percent_fee)
    breakdown["compensation"] = round(eng_comp_score, 3)
    all_signals.extend(comp_signals)

    # 2. Company quality (25%)
    inv_score, _tier1_count, inv_signals = score_investors(investors)
    funding_score, fund_signals = score_funding(funding_amount, funding_stage)
    company_score = (inv_score * 0.5) + (funding_score * 0.5)
    breakdown["company_quality"] = round(company_score, 3)
    all_signals.extend(inv_signals[:2])
    all_signals.extend(fund_signals[:1])

    # 3. Role impact (20%)
    title_lower = title.lower()
    if any(t in title_lower for t in ["head of", "vp", "principal", "staff", "lead"]):
        title_score = 1.0
        all_signals.append("Leadership/senior role")
    elif "senior" in title_lower:
        title_score = 0.8
    else:
        title_score = 0.6

    hiring_count = role_data.get("hiring_count", 1) or 1
    hiring_score = min(1.0, hiring_count / 3)
    if hiring_count >= 3:
        all_signals.append(f"Hiring {hiring_count}+ positions")

    size = company_size or 50
    if 20 <= size <= 100:
        size_score = 1.0
    elif 10 <= size <= 200:
        size_score = 0.8
    else:
        size_score = 0.6

    impact_score = (title_score * 0.5) + (hiring_score * 0.3) + (size_score * 0.2)
    breakdown["role_impact"] = round(impact_score, 3)

    # 4. Process quality (15%)
    eng_process, _, process_signals = score_process_quality(
        manager_rating, resp_days, interview_stages, highlights
    )
    breakdown["process_quality"] = round(eng_process, 3)
    all_signals.extend(process_signals[:2])

    # 5. Tech modernity (10%)
    modern_tech = {"react", "typescript", "python", "go", "rust", "kubernetes", "graphql", "next"}
    tech_lower = {t.lower() for t in tech_stack}
    tech_overlap = len(tech_lower & modern_tech)
    tech_score = min(1.0, tech_overlap / 3)

    hot_industries = {"ai", "fintech", "developer_tools", "cybersecurity", "devtools"}
    industry_lower = {i.lower() for i in industries}
    industry_score = 1.0 if (industry_lower & hot_industries) else 0.5

    tech_modernity = (tech_score * 0.6) + (industry_score * 0.4)
    breakdown["tech_modernity"] = round(tech_modernity, 3)
    if tech_overlap >= 2:
        all_signals.append(f"Modern tech stack ({tech_overlap} matches)")

    # Final weighted score
    final_score = (
        breakdown["compensation"] * 0.30
        + breakdown["company_quality"] * 0.25
        + breakdown["role_impact"] * 0.20
        + breakdown["process_quality"] * 0.15
        + breakdown["tech_modernity"] * 0.10
    )

    return ScoringResult(
        score=round(final_score, 2),
        breakdown=breakdown,
        signals=all_signals[:5],  # Top 5 signals
    )
