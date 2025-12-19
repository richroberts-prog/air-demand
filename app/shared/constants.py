"""Shared constants for demand-side codebase.

Single source of truth for:
- Investor tiers (Tier 1, Tier 2, notable angels)
- Funding stages, industries, role types
- Score thresholds
- Display name mappings

This eliminates duplication across qualification.py, scoring.py, digest.py,
enrichment.py, and frontend components.
"""

from enum import IntEnum
from typing import Literal

# ====================
# Investor Tiers
# ====================


class InvestorTier(IntEnum):
    """Investor tier levels."""

    NONE = 0
    TIER_2 = 2
    TIER_1 = 1  # Elite tier (highest value)


# Canonical lowercase names for matching
TIER_1_INVESTORS: set[str] = {
    "sequoia",
    "sequoia capital",
    "a16z",
    "andreessen horowitz",
    "benchmark",
    "greylock",
    "greylock partners",
    "accel",
    "accel partners",
    "general catalyst",  # TIER 1 (fixes inconsistency)
    "lightspeed",
    "lightspeed venture partners",
    "khosla",
    "khosla ventures",
    "founders fund",
    "kleiner perkins",
    "yc",
    "y combinator",
    "index ventures",
    "gv",
    "google ventures",
    "tiger global",
    "tiger global management",
    "coatue",
    "coatue management",
    "thrive capital",
    "bessemer",
    "bessemer venture partners",
    "insight partners",
    "craft ventures",
    "redpoint",
    "redpoint ventures",
    "nea",
    "new enterprise associates",
    "battery ventures",
}

TIER_2_INVESTORS: set[str] = {
    "spark capital",
    "ivp",
    "institutional venture partners",
    "menlo ventures",
    "felicis",
    "felicis ventures",
    "bain capital ventures",
    "initialized capital",
    "floodgate",
    "first round",
    "first round capital",
    "union square ventures",
    "usv",
    "lux capital",
    "lowercase capital",
    "8vc",
    "nfx",
    "founders collective",
    "gradient ventures",
    "maverick ventures",
    "forerunner ventures",
    "ribbit capital",
}

NOTABLE_ANGELS: set[str] = {
    # Tech legends who angel invest
    "elad gil",
    "nat friedman",
    "daniel gross",
    "max levchin",
    "aaron levie",
    "arash ferdowsi",
    "jack altman",
    "gokul rajaram",
    "paul buchheit",
    "naval ravikant",
    "lachy groom",
    "dylan field",
}

# Display names for UI (canonical → full name)
INVESTOR_DISPLAY_NAMES: dict[str, str] = {
    "sequoia": "Sequoia Capital",
    "sequoia capital": "Sequoia Capital",
    "a16z": "Andreessen Horowitz",
    "andreessen horowitz": "Andreessen Horowitz",
    "benchmark": "Benchmark",
    "greylock": "Greylock Partners",
    "greylock partners": "Greylock Partners",
    "accel": "Accel",
    "accel partners": "Accel",
    "general catalyst": "General Catalyst",
    "lightspeed": "Lightspeed Venture Partners",
    "lightspeed venture partners": "Lightspeed Venture Partners",
    "khosla": "Khosla Ventures",
    "khosla ventures": "Khosla Ventures",
    "founders fund": "Founders Fund",
    "kleiner perkins": "Kleiner Perkins",
    "yc": "Y Combinator",
    "y combinator": "Y Combinator",
    "index ventures": "Index Ventures",
    "gv": "GV",
    "google ventures": "GV",
    "tiger global": "Tiger Global",
    "tiger global management": "Tiger Global",
    "coatue": "Coatue",
    "coatue management": "Coatue",
    "thrive capital": "Thrive Capital",
    "bessemer": "Bessemer Venture Partners",
    "bessemer venture partners": "Bessemer Venture Partners",
    "insight partners": "Insight Partners",
    "craft ventures": "Craft Ventures",
    "redpoint": "Redpoint Ventures",
    "redpoint ventures": "Redpoint Ventures",
    "nea": "NEA",
    "new enterprise associates": "NEA",
    "battery ventures": "Battery Ventures",
    "first round": "First Round Capital",
    "first round capital": "First Round Capital",
    "union square ventures": "Union Square Ventures",
    "usv": "Union Square Ventures",
}

# Short names for compact display (canonical → abbreviated)
INVESTOR_SHORT_NAMES: dict[str, str] = {
    "sequoia": "Sequoia",
    "sequoia capital": "Sequoia",
    "a16z": "a16z",
    "andreessen horowitz": "a16z",
    "benchmark": "Benchmark",
    "greylock": "Greylock",
    "greylock partners": "Greylock",
    "accel": "Accel",
    "general catalyst": "General Catalyst",
    "lightspeed": "Lightspeed",
    "lightspeed venture partners": "Lightspeed",
    "khosla": "Khosla",
    "khosla ventures": "Khosla",
    "founders fund": "Founders Fund",
    "kleiner perkins": "Kleiner Perkins",
    "yc": "YC",
    "y combinator": "YC",
    "index ventures": "Index Ventures",
    "gv": "GV",
    "google ventures": "GV",
    "tiger global": "Tiger Global",
    "thrive capital": "Thrive",
    "bessemer": "Bessemer",
    "insight partners": "Insight",
    "craft ventures": "Craft",
    "redpoint": "Redpoint",
    "nea": "NEA",
    "battery ventures": "Battery",
    "first round": "First Round",
    "first round capital": "First Round",
    "union square ventures": "USV",
    "usv": "USV",
}


# ====================
# Hot Companies
# ====================

HOT_COMPANIES: set[str] = {
    # Known hot companies (bypass LLM for excitement scoring)
    "anthropic",
    "openai",
    "stripe",
    "figma",
    "notion",
    "linear",
    "vercel",
    "supabase",
    "ramp",
    "mercury",
    "plaid",
    "retool",
    "databricks",
    "snowflake",
    "datadog",
    "cloudflare",
}


# ====================
# Funding Stages
# ====================

FUNDING_STAGE_DISPLAY: dict[str, str] = {
    "PRE_SEED": "Pre",
    "SEED": "Seed",
    "SERIES_A": "A",
    "SERIES_B": "B",
    "SERIES_C": "C",
    "SERIES_D": "D",
    "SERIES_E": "E",
    "SERIES_F": "F",
    "SERIES_G": "G+",
}


# ====================
# Industries
# ====================

INDUSTRY_DISPLAY: dict[str, str] = {
    # Tech & Software (most common)
    "software_development": "SW",
    "ai": "AI",
    "devtools": "DevTls",
    "api_sdk": "API",
    "data": "Data",
    "cybersecurity": "Cyber",
    "security": "Sec",
    "hardware": "HW",
    "robotics": "Robots",
    # Finance
    "fintech": "Fintech",
    "finance": "Fin",
    "financial_services": "FinSvc",
    "crypto": "Crypto",
    "venture_capital": "VC",
    "insurance": "Insure",
    # Healthcare & Life Sciences
    "healthcare": "Health",
    "health": "Health",
    "life_sciences": "LifeSc",
    # Enterprise & Business
    "enterprise": "Enterp",
    "b2b": "B2B",
    "saas": "SaaS",
    "ecommerce": "eCom",
    "marketplace": "Mktplc",
    "marketing": "Market",
    "ad_tech": "AdTech",
    # Industry & Infrastructure
    "defense": "Def",
    "government": "Gov",
    "law": "Law",
    "construction": "Constr",
    "manufacturing": "Manufa",
    "logistics": "Logist",
    "transportation": "Transp",
    "autonomous_vehicles": "AutoV",
    "real_estate": "RealEt",
    # Consumer & Media
    "consumer": "Consum",
    "gaming": "Gaming",
    "media": "Media",
    "creator_economy": "Create",
    "education": "Edu",
    # Legacy mappings (still in some data)
    "climate": "Climat",
    "web3": "Web3",
    "edtech": "EdTech",
    "proptech": "PropTc",
    "biotech": "BioTch",
}


# ====================
# Role Types
# ====================

ROLE_TYPE_DISPLAY: dict[str, str] = {
    "backend_engineer": "Backend",
    "frontend_engineer": "Frontend",
    "full_stack_engineer": "Full Stack",
    "ml_engineer": "ML",
    "machine_learning_engineer": "ML",
    "devops_engineer": "DevOps",
    "data_engineer": "Data",
    "infrastructure_engineer": "Infrastructure",
    "infrastructure_devops_sre": "Infra/DevOps",
    "platform_engineer": "Platform",
    "site_reliability_engineer": "SRE",
    "security_engineer": "Security",
    "solutions_engineer": "Solutions",
    "embedded_firmware_engineer": "Embedded",
    "electrical_engineer": "Electrical",
    "mechanical_engineer": "Mechanical",
    "forward_deployed_engineer_solutions_support": "Solutions",
}


# ====================
# Locations
# ====================

LOCATION_DISPLAY: dict[str, str] = {
    # Major US cities (max 4 chars for compact display)
    "new_york": "NYC",
    "san_francisco": "SF",
    "south_bay_area": "SJ",  # San Jose / South Bay
    "washington_dc": "DC",
    "los_angeles": "LA",
    "seattle": "SEA",
    "boston": "BOS",
    "chicago": "CHI",
    "denver": "DEN",
    "austin": "AUS",
    "miami": "MIA",
    "portland": "PDX",
    "phoenix": "PHX",
    # States
    "texas": "TX",
    "california": "CA",
    "colorado": "CO",
    "florida": "FL",
    "washington": "WA",
    # Countries (max 4 chars)
    "canada": "CAN",
    "uk": "UK",
    "india": "IND",
    "australia": "AUS",
    "mexico": "MEX",
    "brazil": "BRA",
    # Regions (max 4 chars)
    "europe": "EUR",
    "asia": "ASIA",
    "latam": "LATM",
}


# ====================
# Location Sets for Qualification
# ====================

# Geographic location sets for qualification
NYC_METRO_LOCATIONS: set[str] = {
    "new_york",
    "new_york_city",
    "nyc",
    "manhattan",
    "brooklyn",
    "queens",
    "bronx",
    "staten_island",
    "jersey_city",
    "hoboken",
    "newark",
}

LONDON_LOCATIONS: set[str] = {
    "london",
    "greater_london",
    "city_of_london",
    "uk",
    "united_kingdom",
}

# All supported locations for qualification (NYC + London only)
SUPPORTED_LOCATIONS: set[str] = NYC_METRO_LOCATIONS | LONDON_LOCATIONS

# Display names for location groups (for dashboard filter)
LOCATION_GROUP_DISPLAY: dict[str, set[str]] = {
    "NYC": NYC_METRO_LOCATIONS,
    "London": LONDON_LOCATIONS,
}


# ====================
# Score Thresholds
# ====================

SCORE_THRESHOLD_HIGH = 0.85  # High-quality role
SCORE_THRESHOLD_MEDIUM = 0.70  # Medium-quality role

ScoreTier = Literal["high", "medium", "low", "none"]


# ====================
# Helper Functions
# ====================


def normalize_investor_name(name: str) -> str:
    """Normalize investor name to canonical lowercase form.

    Args:
        name: Investor name in any format

    Returns:
        Lowercase, stripped canonical name

    Examples:
        >>> normalize_investor_name("Sequoia Capital")
        'sequoia capital'
        >>> normalize_investor_name("  A16z  ")
        'a16z'
    """
    return name.lower().strip()


def get_investor_tier(name: str) -> InvestorTier:
    """Get the tier for a given investor name.

    Args:
        name: Investor name (any format, case-insensitive)

    Returns:
        InvestorTier.TIER_1, InvestorTier.TIER_2, or InvestorTier.NONE

    Examples:
        >>> get_investor_tier("Sequoia Capital")
        <InvestorTier.TIER_1: 1>
        >>> get_investor_tier("General Catalyst")
        <InvestorTier.TIER_1: 1>
        >>> get_investor_tier("First Round")
        <InvestorTier.TIER_2: 2>
        >>> get_investor_tier("Random VC")
        <InvestorTier.NONE: 0>
    """
    canonical = normalize_investor_name(name)

    if canonical in TIER_1_INVESTORS:
        return InvestorTier.TIER_1
    elif canonical in TIER_2_INVESTORS:
        return InvestorTier.TIER_2
    else:
        return InvestorTier.NONE


def get_investor_display_name(name: str) -> str:
    """Get the display name for an investor.

    Args:
        name: Investor name (any format)

    Returns:
        Full display name, or original name if not found

    Examples:
        >>> get_investor_display_name("a16z")
        'Andreessen Horowitz'
        >>> get_investor_display_name("sequoia")
        'Sequoia Capital'
    """
    canonical = normalize_investor_name(name)
    return INVESTOR_DISPLAY_NAMES.get(canonical, name)


def get_investor_short_name(name: str) -> str:
    """Get the short name for an investor.

    Args:
        name: Investor name (any format)

    Returns:
        Abbreviated name, or original name if not found

    Examples:
        >>> get_investor_short_name("Andreessen Horowitz")
        'a16z'
        >>> get_investor_short_name("Sequoia Capital")
        'Sequoia'
    """
    canonical = normalize_investor_name(name)
    return INVESTOR_SHORT_NAMES.get(canonical, name)


def is_tier1_investor(name: str) -> bool:
    """Check if an investor is Tier 1.

    Args:
        name: Investor name (any format)

    Returns:
        True if Tier 1, False otherwise

    Examples:
        >>> is_tier1_investor("General Catalyst")
        True
        >>> is_tier1_investor("First Round")
        False
    """
    return get_investor_tier(name) == InvestorTier.TIER_1


def is_notable_angel(name: str) -> bool:
    """Check if an investor is a notable angel.

    Args:
        name: Investor name (any format)

    Returns:
        True if notable angel, False otherwise

    Examples:
        >>> is_notable_angel("Elad Gil")
        True
        >>> is_notable_angel("Random Person")
        False
    """
    canonical = normalize_investor_name(name)
    return canonical in NOTABLE_ANGELS
