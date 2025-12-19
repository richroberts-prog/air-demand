"""LLM enrichment for company excitement scoring.

Uses Pydantic AI with OpenRouter (Gemini Flash) to assess company excitement
for cases where deterministic scoring is uncertain (0.50-0.70 range).

Enrichment is cached per company (not per role) to minimize API costs.
Only called for QUALIFIED/MAYBE roles.
"""

import os
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.demand.models import CompanyEnrichment

logger = get_logger(__name__)

# Model to use for enrichment (Gemini Flash Lite is cheapest and fastest)
ENRICHMENT_MODEL = "google/gemini-2.5-flash-lite"


class CompanyExcitementResult(BaseModel):
    """LLM assessment of company excitement.

    The LLM returns this structured output when evaluating
    how exciting a company would be to a top 1% engineer.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Excitement score from 0.0 (boring) to 1.0 (extremely exciting). "
        "Be calibrated: 0.9+ should be rare (Anthropic, Figma-level companies only).",
    )
    reasoning: str = Field(
        description="1-2 sentence explanation of the score. "
        "Focus on what makes this company exciting or not.",
    )
    signals: list[str] = Field(
        default_factory=list,
        description="Key signals identified (e.g., 'Strong investor backing', 'Hot AI space').",
    )


def _get_enrichment_agent() -> Agent[None, CompanyExcitementResult]:
    """Create enrichment agent with structured output.

    Returns:
        Pydantic AI Agent configured for company excitement assessment.
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        raise ValueError(
            "OPENROUTER_API_KEY must be set for enrichment. "
            "Get your key from https://openrouter.ai/keys"
        )

    # Set API key in environment for OpenRouter
    os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

    model = OpenRouterModel(ENRICHMENT_MODEL)

    agent: Agent[None, CompanyExcitementResult] = Agent(
        model,
        output_type=CompanyExcitementResult,
        system_prompt="""You are an expert on the startup ecosystem with deep knowledge of
Y Combinator, top VC firms, and what makes companies attractive to elite engineers.

Your task: Rate how exciting a company would be to a TOP 1% SOFTWARE ENGINEER.
These engineers have options at FAANG, well-funded startups, and can be picky.

What makes a company exciting to them:
- World-class investors (Tier 1: Sequoia, a16z, Benchmark, Y Combinator, General Catalyst, Greylock, Accel, Founders Fund, Kleiner Perkins, Index Ventures, Tiger Global, Coatue, and others)
- Founders with strong pedigree (ex-Stripe, ex-Google, Stanford/MIT dropouts)
- Hot problem space (AI, developer tools, fintech)
- Rapid growth signals (recent large raise, hiring aggressively)
- Strong tech culture (known for engineering excellence)
- Mission that matters (not just another B2B SaaS)

What makes a company LESS exciting:
- Unknown or purely financial investors
- Crowded market with no differentiation
- Legacy tech or boring problem space
- Signs of struggle (layoffs, stagnant growth)
- Bad Glassdoor/word-of-mouth reputation

CALIBRATION GUIDE:
- 0.90-1.00: Generational companies (Anthropic, OpenAI, Stripe pre-IPO)
- 0.80-0.89: Elite tier (Ramp, Mercury, Figma before Adobe)
- 0.70-0.79: Strong companies (well-funded, good investors, interesting space)
- 0.60-0.69: Solid but not exciting (good job, not resume highlight)
- 0.50-0.59: Average (fine company, nothing special)
- 0.40-0.49: Below average (concerns about company or space)
- Below 0.40: Avoid (red flags present)

Be honest and critical. Most companies should be 0.50-0.70.""",
    )

    return agent


def _build_enrichment_context(
    company_name: str,
    one_liner: str | None,
    industries: list[str],
    investors: list[str],
    funding_amount: str | None,
    funding_stage: str | None,
    founding_year: int | None,
    company_size: int | None,
) -> str:
    """Build context string for LLM enrichment.

    Args:
        company_name: Company name
        one_liner: Company one-liner description
        industries: List of industries
        investors: List of investor names
        funding_amount: Total funding raised
        funding_stage: Current funding stage
        founding_year: Year company was founded
        company_size: Number of employees

    Returns:
        Formatted context string for LLM
    """
    parts = [f"Company: {company_name}"]

    if one_liner:
        parts.append(f"Description: {one_liner}")

    if industries:
        parts.append(f"Industries: {', '.join(industries)}")

    if investors:
        parts.append(f"Investors: {', '.join(investors)}")

    if funding_amount:
        parts.append(f"Funding raised: {funding_amount}")

    if funding_stage:
        parts.append(f"Funding stage: {funding_stage.replace('_', ' ').title()}")

    if founding_year:
        parts.append(f"Founded: {founding_year}")

    if company_size:
        parts.append(f"Team size: ~{company_size} employees")

    return "\n".join(parts)


async def get_cached_enrichment(
    db: AsyncSession,
    company_name: str,
) -> CompanyEnrichment | None:
    """Get cached enrichment for a company.

    Args:
        db: Database session
        company_name: Normalized company name (lowercase, stripped)

    Returns:
        Cached CompanyEnrichment or None if not found
    """
    stmt = select(CompanyEnrichment).where(
        CompanyEnrichment.company_name == company_name.lower().strip()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def enrich_company(
    company_name: str,
    one_liner: str | None,
    industries: list[str],
    investors: list[str],
    funding_amount: str | None,
    funding_stage: str | None,
    founding_year: int | None,
    company_size: int | None,
    db: AsyncSession,
) -> CompanyEnrichment:
    """Get or create company enrichment with LLM.

    Checks cache first, then calls LLM if not found.
    Results are cached per company (not per role).

    Args:
        company_name: Company name
        one_liner: Company one-liner description
        industries: List of industries
        investors: List of investor names
        funding_amount: Total funding raised (e.g., "$17.3M")
        funding_stage: Current funding stage (e.g., "SERIES_A")
        founding_year: Year company was founded
        company_size: Number of employees
        db: Database session

    Returns:
        CompanyEnrichment (from cache or freshly created)
    """
    normalized_name = company_name.lower().strip()

    # Check cache first
    cached = await get_cached_enrichment(db, normalized_name)
    if cached:
        logger.info(
            "jobs.enrichment.cache_hit",
            company=company_name,
            cached_score=cached.excitement_score,
        )
        return cached

    # Build context for LLM
    context = _build_enrichment_context(
        company_name=company_name,
        one_liner=one_liner,
        industries=industries,
        investors=investors,
        funding_amount=funding_amount,
        funding_stage=funding_stage,
        founding_year=founding_year,
        company_size=company_size,
    )

    # Store context for debugging
    context_used: dict[str, Any] = {
        "company_name": company_name,
        "one_liner": one_liner,
        "industries": industries,
        "investors": investors,
        "funding_amount": funding_amount,
        "funding_stage": funding_stage,
        "founding_year": founding_year,
        "company_size": company_size,
    }

    logger.info("jobs.enrichment.llm_call_started", company=company_name)

    try:
        # Call LLM
        agent = _get_enrichment_agent()
        result = await agent.run(f"Assess this company:\n\n{context}")

        llm_result = result.output

        logger.info(
            "jobs.enrichment.llm_call_completed",
            company=company_name,
            score=llm_result.score,
            reasoning=llm_result.reasoning[:100] + "..."
            if len(llm_result.reasoning) > 100
            else llm_result.reasoning,
        )

    except Exception as e:
        logger.error(
            "jobs.enrichment.llm_call_failed",
            company=company_name,
            error=str(e),
            exc_info=True,
        )
        # Return a default enrichment on failure (don't crash scoring)
        llm_result = CompanyExcitementResult(
            score=0.50,
            reasoning=f"LLM enrichment failed: {str(e)[:100]}",
            signals=["Enrichment error - using default score"],
        )

    # Cache result
    now = datetime.now(UTC)
    enrichment = CompanyEnrichment(
        company_name=normalized_name,
        excitement_score=llm_result.score,
        reasoning=llm_result.reasoning,
        signals=llm_result.signals,
        enriched_at=now,
        model_version=ENRICHMENT_MODEL,
        context_used=context_used,
        created_at=now,
        updated_at=now,
    )

    db.add(enrichment)
    await db.flush()  # Flush to get the ID, but don't commit yet

    logger.info(
        "jobs.enrichment.cached",
        company=company_name,
        enrichment_id=enrichment.id,
        score=enrichment.excitement_score,
    )

    return enrichment


async def should_enrich(
    deterministic_excitement_score: float,
    qualification_tier: str | None,
) -> bool:
    """Determine if a company should be enriched with LLM.

    Only enriches when:
    1. Role is QUALIFIED or MAYBE tier
    2. Deterministic excitement score is in uncertain range (0.50-0.70)

    Args:
        deterministic_excitement_score: Score from scoring.py
        qualification_tier: Role qualification tier

    Returns:
        True if enrichment should be performed
    """
    # Only enrich qualified roles
    if qualification_tier not in ("QUALIFIED", "MAYBE"):
        return False

    # Only enrich uncertain scores
    if 0.50 <= deterministic_excitement_score <= 0.70:
        return True

    return False


async def enrich_company_from_role_data(
    role_data: dict[str, Any],
    db: AsyncSession,
) -> CompanyEnrichment | None:
    """Convenience function to enrich company from raw role data.

    Extracts company info from role data and calls enrich_company.

    Args:
        role_data: Raw tRPC response for a role
        db: Database session

    Returns:
        CompanyEnrichment or None if company name missing
    """
    company = role_data.get("company", {})
    company_name = company.get("name")

    if not company_name:
        logger.warning("jobs.enrichment.missing_company_name")
        return None

    # Extract company metadata
    company_metadata = company.get("company_metadata", {})

    return await enrich_company(
        company_name=company_name,
        one_liner=company.get("oneLiner"),
        industries=company.get("industries", []),
        investors=role_data.get("investors", []),
        funding_amount=company.get("fundingAmount"),
        funding_stage=company_metadata.get("last_funding_round"),
        founding_year=company.get("foundingYear"),
        company_size=company.get("size"),
        db=db,
    )
