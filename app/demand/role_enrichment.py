"""Role enrichment via LLM extraction from HTML fields.

Extracts structured intel from companyTip and selling_points HTML:
- Investors (VCs)
- Notable angels/advisors
- Funding stage
- Founder background
- Company stage signals
- Process speed indicators
- Risk/runway signals

Uses Pydantic AI with OpenRouter (Gemini Flash) for extraction.
Results cached per role to minimize API costs.
"""

import os
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.demand.models import RoleEnrichment

logger = get_logger(__name__)

# Model to use for extraction (Gemini Flash Lite is cheapest and fastest)
EXTRACTION_MODEL = "google/gemini-2.5-flash-lite"


class ExtractedRoleIntel(BaseModel):
    """Structured intel extracted from role HTML fields.

    Contains all scoring-relevant signals extracted from
    companyTip and selling_points HTML.
    """

    # Investors
    investors: list[str] = Field(
        default_factory=list,
        description="List of VC/investor firm names. Use canonical names "
        "(e.g., 'Andreessen Horowitz' not 'a16z', 'Y Combinator' not 'YC').",
    )
    angels: list[str] = Field(
        default_factory=list,
        description="Notable angel investors or advisors with their titles/backgrounds. "
        "Format: 'Name (Title/Background)' e.g., 'John Smith (former CEO of Stripe)'.",
    )

    # Funding
    funding_stage: str | None = Field(
        default=None,
        description="Funding stage if mentioned: 'Pre-seed', 'Seed', 'Series A', 'Series B', etc.",
    )
    funding_amount: str | None = Field(
        default=None,
        description="Funding amount if mentioned, e.g., '$15.5M', '$100M'.",
    )

    # Founder/leadership
    founder_background: str | None = Field(
        default=None,
        description="Notable founder/CEO background if mentioned (e.g., 'ex-Stripe', 'Stanford dropout').",
    )

    # Company stage signals
    employee_count: int | None = Field(
        default=None,
        description="Team size if mentioned (e.g., 'Employee #6' means ~5 employees).",
    )
    growth_stage: str | None = Field(
        default=None,
        description="Stage signals: 'ground zero', 'scaling', 'early stage', 'established', etc.",
    )

    # Process signals (headhunter-relevant)
    process_speed: str | None = Field(
        default=None,
        description="Hiring speed signals: 'fast process', 'close in 1-2 weeks', 'urgent', etc.",
    )
    urgency_level: str | None = Field(
        default=None,
        description="Urgency: 'ASAP', 'urgent', 'immediate need', or None if not mentioned.",
    )

    # Risk/runway signals
    runway_signal: str | None = Field(
        default=None,
        description="Runway/stability signals: 'extensive runway', 'well-funded', 'de-risked'.",
    )
    partnerships: list[str] = Field(
        default_factory=list,
        description="Key partnerships or design partners mentioned.",
    )

    # Location extraction
    extracted_location: str | None = Field(
        default=None,
        description="Primary work location if mentioned in text. Use canonical city names: "
        "'New York', 'London', 'San Francisco', 'Boston', 'Austin'. "
        "If remote-first or fully remote, use 'Remote'. "
        "If multiple locations, pick the PRIMARY office/HQ location. "
        "If no location mentioned, leave null (don't guess).",
    )
    location_confidence: str | None = Field(
        default=None,
        description="Confidence in location extraction: "
        "'high' (explicit mention like 'based in SF' or 'London office'), "
        "'medium' (implied like 'our office is in...' or company context), "
        "'low' (ambiguous or inferred from weak signals). "
        "If no location extracted, leave null.",
    )

    # Positive signals (for scoring boost)
    positive_signals: list[str] = Field(
        default_factory=list,
        description="List of positive signals that would attract top engineers. "
        "E.g., 'Tier-1 investors', 'Experienced founder', 'Fast hiring process'.",
    )

    # Negative signals (for scoring penalty)
    negative_signals: list[str] = Field(
        default_factory=list,
        description="List of concerning signals. "
        "E.g., 'Unknown investors', 'Vague product description', 'Red flags'.",
    )


def _strip_html(html: str | None) -> str:
    """Remove HTML tags and clean whitespace."""
    if not html:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Clean whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _get_extraction_agent() -> Agent[None, ExtractedRoleIntel]:
    """Create extraction agent with structured output.

    Returns:
        Pydantic AI Agent configured for role intel extraction.
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        raise ValueError(
            "OPENROUTER_API_KEY must be set for enrichment. "
            "Get your key from https://openrouter.ai/keys"
        )

    # Set API key in environment for OpenRouter
    os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

    model = OpenRouterModel(EXTRACTION_MODEL)

    agent: Agent[None, ExtractedRoleIntel] = Agent(
        model,
        output_type=ExtractedRoleIntel,
        system_prompt="""You are an expert at extracting structured information from startup job posting descriptions.

Your task: Extract all scoring-relevant intel from the provided text.

INVESTOR EXTRACTION:
- Extract VC firm names using CANONICAL forms (not abbreviations):
  - "a16z" → "Andreessen Horowitz"
  - "yc" or "Y Combinator" → "Y Combinator"
  - "gc" → "General Catalyst"
- Keep firm names clean (no "backed by" or "invested by" prefixes)
- Separate VCs from angel investors

SIGNAL EXTRACTION:
- Positive signals: tier-1 investors, experienced founders, fast process, strong runway
- Negative signals: unknown investors, vague descriptions, concerning patterns
- Be specific and actionable in signal descriptions

LOCATION EXTRACTION:
- Extract the PRIMARY work location if explicitly mentioned in the text
- Use canonical city names: "New York", "London", "San Francisco", "Boston", "Austin"
- If explicitly remote/distributed/remote-first, extract "Remote"
- If multiple locations mentioned, pick the HQ or primary office
- Confidence levels:
  - High: "Based in SF", "London office", "NYC-based", "Austin HQ"
  - Medium: "Our office is in Boston", "Team located in..."
  - Low: Inferred from company context, ambiguous mentions
- If no location mentioned, leave null (don't guess or infer)

GENERAL RULES:
- Only extract information explicitly stated in the text
- Don't infer or guess - if something isn't mentioned, leave it null/empty
- For employee count, extract the number (e.g., "Employee #6" means ~5 current)
- For funding, extract both stage and amount if available""",
    )

    return agent


async def get_cached_enrichment(
    db: AsyncSession,
    paraform_id: str,
) -> RoleEnrichment | None:
    """Get cached enrichment for a role.

    Args:
        db: Database session
        paraform_id: Role ID to look up

    Returns:
        Cached RoleEnrichment or None if not found
    """
    stmt = select(RoleEnrichment).where(RoleEnrichment.paraform_id == paraform_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def enrich_role_from_html(
    paraform_id: str,
    company_tip: str | None,
    selling_points: str | None,
    db: AsyncSession,
) -> RoleEnrichment | None:
    """Extract intel from role HTML fields using LLM.

    Checks cache first, then calls LLM if not found.
    Results cached per role.

    Args:
        paraform_id: Paraform role ID
        company_tip: companyTip HTML from getRoleByIdSimple
        selling_points: selling_points HTML from getRoleByIdSimple
        db: Database session

    Returns:
        RoleEnrichment with extracted data, or None if no text to extract from
    """
    # Check cache first
    cached = await get_cached_enrichment(db, paraform_id)
    if cached:
        logger.info(
            "jobs.role_enrichment.cache_hit",
            paraform_id=paraform_id,
            investors_count=len(cached.investors),
        )
        return cached

    # Check if we have content to extract from
    if not company_tip and not selling_points:
        logger.info(
            "jobs.role_enrichment.no_content",
            paraform_id=paraform_id,
        )
        return None

    # Strip HTML and combine text
    tip_text = _strip_html(company_tip)
    points_text = _strip_html(selling_points)
    combined_text = f"{tip_text}\n\n{points_text}".strip()

    if not combined_text:
        return None

    logger.info(
        "jobs.role_enrichment.extraction_started",
        paraform_id=paraform_id,
        text_length=len(combined_text),
    )

    try:
        # Call LLM
        agent = _get_extraction_agent()
        result = await agent.run(
            f"Extract structured intel from this job posting text:\n\n{combined_text}"
        )

        extracted = result.output

        logger.info(
            "jobs.role_enrichment.extraction_completed",
            paraform_id=paraform_id,
            investors_count=len(extracted.investors),
            angels_count=len(extracted.angels),
            positive_signals=len(extracted.positive_signals),
        )

    except Exception as e:
        logger.error(
            "jobs.role_enrichment.extraction_failed",
            paraform_id=paraform_id,
            error=str(e),
            exc_info=True,
        )
        # Return empty enrichment on failure (don't crash scraping)
        extracted = ExtractedRoleIntel()

    # Build extracted_data JSONB from the structured result
    extracted_data: dict[str, Any] = {
        "investors": extracted.investors,
        "angels": extracted.angels,
        "funding_stage": extracted.funding_stage,
        "funding_amount": extracted.funding_amount,
        "founder_background": extracted.founder_background,
        "employee_count": extracted.employee_count,
        "growth_stage": extracted.growth_stage,
        "process_speed": extracted.process_speed,
        "urgency_level": extracted.urgency_level,
        "runway_signal": extracted.runway_signal,
        "partnerships": extracted.partnerships,
        "extracted_location": extracted.extracted_location,
        "location_confidence": extracted.location_confidence,
    }

    # Create and cache enrichment
    now = datetime.now(UTC)
    enrichment = RoleEnrichment(
        paraform_id=paraform_id,
        extracted_data=extracted_data,
        positive_signals=extracted.positive_signals,
        negative_signals=extracted.negative_signals,
        investors=extracted.investors,
        funding_stage=extracted.funding_stage,
        extracted_location=extracted.extracted_location,
        extracted_location_confidence=extracted.location_confidence,
        source_company_tip=company_tip,
        source_selling_points=selling_points,
        enriched_at=now,
        model_version=EXTRACTION_MODEL,
        created_at=now,
        updated_at=now,
    )

    db.add(enrichment)
    await db.flush()

    logger.info(
        "jobs.role_enrichment.cached",
        paraform_id=paraform_id,
        enrichment_id=enrichment.id,
    )

    return enrichment


def merge_enrichment_into_role_data(
    role_data: dict[str, Any],
    enrichment: RoleEnrichment,
) -> dict[str, Any]:
    """Merge extracted enrichment data into role_data for scoring.

    Updates the investors array and adds other signals.

    Args:
        role_data: Raw role data dict from API
        enrichment: Extracted enrichment data

    Returns:
        Updated role_data with merged enrichment
    """
    # Merge investors (combine existing with extracted)
    existing_investors = set(role_data.get("investors", []))
    extracted_investors = set(enrichment.investors or [])
    role_data["investors"] = list(existing_investors | extracted_investors)

    # Add extracted signals to role_data for scoring access
    role_data["_enrichment"] = {
        "extracted_data": enrichment.extracted_data,
        "positive_signals": enrichment.positive_signals,
        "negative_signals": enrichment.negative_signals,
        "funding_stage": enrichment.funding_stage,
    }

    return role_data
