"""FastAPI routes for shared constants and utilities.

Exposes shared constants (investors, stages, industries, etc.) to frontend
via REST API for consistent data across backend and frontend.
"""

from fastapi import APIRouter

from app.shared.constants import (
    HOT_COMPANIES,
    NOTABLE_ANGELS,
    SCORE_THRESHOLD_HIGH,
    SCORE_THRESHOLD_MEDIUM,
    TIER_1_INVESTORS,
    TIER_2_INVESTORS,
)

router = APIRouter(prefix="/shared", tags=["shared"])


@router.get("/constants")
async def get_constants() -> dict[str, object]:
    """Get all shared constants.

    Returns:
        Dictionary with all shared constants including:
        - investors: Tier 1 and Tier 2 VCs, notable angels
        - companies: Hot companies list
        - thresholds: Score thresholds for qualification tiers

    Example response:
        {
            "investors": {
                "tier_1": ["sequoia", "a16z", ...],
                "tier_2": ["spark capital", ...],
                "notable_angels": ["elad gil", ...]
            },
            "companies": {
                "hot": ["openai", "anthropic", ...]
            },
            "thresholds": {
                "high": 0.85,
                "medium": 0.70
            }
        }
    """
    return {
        "investors": {
            "tier_1": sorted(list(TIER_1_INVESTORS)),
            "tier_2": sorted(list(TIER_2_INVESTORS)),
            "notable_angels": sorted(list(NOTABLE_ANGELS)),
        },
        "companies": {
            "hot": sorted(list(HOT_COMPANIES)),
        },
        "thresholds": {
            "high": SCORE_THRESHOLD_HIGH,
            "medium": SCORE_THRESHOLD_MEDIUM,
        },
    }
