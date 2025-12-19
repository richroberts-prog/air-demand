"""Excitement scoring for company evaluation.

Calculates how exciting/prestigious a company is based on:
- Known hot companies
- Investor quality (tier-1 VCs, notable angels)
- Funding momentum
- Hot industry (AI, fintech, etc.)
- Recent founding + growth signals
"""

from app.core.logging import get_logger
from app.shared.constants import (
    HOT_COMPANIES,
    NOTABLE_ANGELS,
    TIER_1_INVESTORS,
    TIER_2_INVESTORS,
)
from app.shared.formatting import parse_funding_amount

logger = get_logger(__name__)


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
    angel_count = 0

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

        # Check notable angels
        elif any(angel in inv_lower for angel in NOTABLE_ANGELS):
            angel_count += 1
            if len(signals) < 3:
                signals.append(f"Notable angel: {inv}")

    # Calculate score: tier1 = 0.3 each (max 0.9), tier2/angels = 0.15 each
    score = min(1.0, tier1_count * 0.30 + tier2_count * 0.15 + angel_count * 0.15)

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
# Excitement Scoring (Deterministic)
# ====================


def score_excitement_deterministic(
    company_name: str,
    investors: list[str],
    funding_amount: str | None,
    funding_stage: str | None,  # Reserved for future use  # noqa: ARG001
    industries: list[str] | None,
    founding_year: int | None,
    company_size: int | None,
    title: str | None,
) -> tuple[float, list[str]]:
    """Calculate company excitement score using deterministic signals.

    This is the algorithmic excitement score. LLM enrichment (in enrichment.py)
    can enhance this for uncertain cases (0.50-0.70 range).

    Args:
        company_name: Company name
        investors: List of investors
        funding_amount: Funding raised
        funding_stage: Current funding stage
        industries: Company industries
        founding_year: Year founded
        company_size: Team size
        title: Role title (senior roles at hot companies = more exciting)

    Returns:
        Tuple of (score 0.0-1.0, signals)
    """
    signals: list[str] = []
    score = 0.0

    # Check if it's a known hot company
    if company_name.lower().strip() in HOT_COMPANIES:
        return 0.95, [f"Known hot company: {company_name}"]

    # Investor quality (up to 0.40)
    inv_score, tier1_count, inv_signals = score_investors(investors)
    if tier1_count >= 3:
        score += 0.40
        signals.append(f"{tier1_count} tier-1 investors")
    elif tier1_count >= 2:
        score += 0.30
        signals.extend(inv_signals[:2])
    elif tier1_count >= 1:
        score += 0.20
        signals.extend(inv_signals[:1])
    else:
        score += inv_score * 0.15

    # Funding momentum (up to 0.25)
    funding_usd = parse_funding_amount(funding_amount)
    if funding_usd >= 100_000_000:
        score += 0.25
        signals.append(f"${funding_usd / 1_000_000:.0f}M raised (unicorn trajectory)")
    elif funding_usd >= 30_000_000:
        score += 0.20
        signals.append(f"${funding_usd / 1_000_000:.0f}M raised")
    elif funding_usd >= 10_000_000:
        score += 0.15
    elif funding_usd >= 5_000_000:
        score += 0.10

    # Hot industry (up to 0.15)
    industries_lower = {i.lower() for i in (industries or [])}
    if industries_lower & {"ai", "artificial_intelligence", "machine_learning"}:
        score += 0.15
        signals.append("AI company")
    elif industries_lower & {"developer_tools", "devtools", "fintech", "cybersecurity"}:
        score += 0.10
        signals.append("Hot industry")

    # Recent founding + growth (up to 0.10)
    year = founding_year or 2020
    if year >= 2022:
        score += 0.05
        signals.append(f"Founded {year} (recent)")

    # Company size sweet spot (up to 0.05)
    size = company_size or 50
    if 20 <= size <= 100:
        score += 0.05

    # Senior role boost (up to 0.05)
    title_lower = (title or "").lower()
    if any(t in title_lower for t in ["head of", "vp", "principal", "staff"]):
        score += 0.05
        signals.append("Senior/leadership role")

    return min(1.0, score), signals
