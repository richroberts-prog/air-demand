"""Company/role profile extraction for outreach generation.

Phase 1: Build structured profile from Paraform Browse/Detail APIs + LLM extraction.
Profile is used to GENERATE outreach messages (not the briefing itself).
Gaps marked with [RESEARCH NEEDED] for Phase 2 web research.

Profile Structure:
- Problem/Solution context (for hook generation)
- Credibility signals (team, funding, traction)
- Role details (responsibility, day-to-day, impact)
- Requirements (must-haves, nice-to-haves)
- Interview intel (process, prep)
- Risk signals (red flags)

Header metadata (company, stage, compensation) comes from Browse API separately.
"""

import asyncio
import os
import re
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

EXTRACTION_MODEL = "google/gemini-2.5-flash"


class ProblemContext(BaseModel):
    """Problem/solution framing for outreach hooks."""

    problem_statement: str | None = Field(
        default=None,
        description="What pain point does this company solve? 1-2 sentences. Extract from description or mark as [RESEARCH NEEDED]",
    )
    technical_challenge: str | None = Field(
        default=None,
        description="Core technical problem they're solving. 1 sentence. Extract from description or mark as [RESEARCH NEEDED]",
    )
    solution_approach: str | None = Field(
        default=None,
        description="How they're solving it differently than competitors. 1 sentence. Extract from description or mark as [RESEARCH NEEDED]",
    )
    why_now: str | None = Field(
        default=None,
        description="Why this is urgent/timely (funding, launch, market timing). Extract from description or mark as [RESEARCH NEEDED]",
    )


class CredibilitySignals(BaseModel):
    """Team, funding, and traction signals (mostly from web research)."""

    founder_background: str | None = Field(
        default=None,
        description="Founder background if mentioned in description. Otherwise: [RESEARCH NEEDED: Founder LinkedIn]",
    )
    team_pedigree: str | None = Field(
        default=None,
        description="Team backgrounds if mentioned (e.g., 'Ex-Stripe, Plaid engineers'). Otherwise: [RESEARCH NEEDED: Team LinkedIn]",
    )
    traction_metrics: str | None = Field(
        default=None,
        description="ARR, customers, growth % if mentioned. Otherwise: [RESEARCH NEEDED: Company blog/Crunchbase]",
    )
    customer_status: str | None = Field(
        default=None,
        description="Customer/launch status if mentioned (e.g., 'Early customers live, launching Q1'). Otherwise: [RESEARCH NEEDED]",
    )


class RoleDetails(BaseModel):
    """What the engineer will own and do."""

    core_responsibility: str = Field(
        description="Primary ownership area in 1 sentence (e.g., 'Build the orchestration layer for financial data sync')"
    )
    day_to_day_tasks: list[str] = Field(
        description="3-5 specific tasks. Start with verbs. Be specific (not 'work with team').",
        default_factory=list,
    )
    impact_statement: str | None = Field(
        default=None,
        description="Why this role matters (e.g., 'Your decisions = company's technical foundation')",
    )


class InterviewProcess(BaseModel):
    """Interview process and prep intel."""

    stages: list[str] = Field(
        description="Stage descriptions (e.g., '1. Recruiter screen (30min) - Experience fit'). Use generic template if not in description.",
        default_factory=list,
    )
    evaluation_criteria: list[str] = Field(
        description="What they're evaluating (infer from requirements). Format as questions.",
        default_factory=list,
    )
    prep_needed: list[str] = Field(
        description="What candidate should prep (e.g., 'Have ready 2-3 API integration examples')",
        default_factory=list,
    )


class RoleProfile(BaseModel):
    """Structured company/role profile for outreach generation - Phase 1."""

    # Problem/solution context (for hooks)
    problem: ProblemContext

    # Credibility signals (mostly gaps for Phase 2)
    credibility: CredibilitySignals

    # Role details
    role: RoleDetails

    # Requirements (from Paraform Detail API)
    must_haves: list[str] = Field(
        description="Deal-breaker requirements. Format: '[Quantifier]: [Requirement (context)]'",
        default_factory=list,
    )
    nice_to_haves: list[str] = Field(
        description="Preferred requirements. Same format as must-haves.",
        default_factory=list,
    )

    # Interview intel
    interview: InterviewProcess

    # Risk signals
    red_flags: list[str] = Field(
        description="Concerning signals. Format: '[Signal] = [Risk interpretation]'",
        default_factory=list,
    )


def _get_profile_agent() -> Agent[None, RoleProfile]:
    """Create profile extraction agent with structured output."""
    settings = get_settings()
    os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

    model = OpenRouterModel(EXTRACTION_MODEL)

    agent: Agent[None, RoleProfile] = Agent(
        model,
        output_type=RoleProfile,
        system_prompt="""You are an expert executive recruiter building company/role profiles for outreach generation.

Your task: Extract structured profile data from role description. This is Phase 1 - extract what you can, mark gaps with [RESEARCH NEEDED].

FORMAT RULES:
- Dense, specific bullets (not paragraphs)
- Use [RESEARCH NEEDED: X] when information isn't in description
- Add context in parentheses to clarify
- NO generic phrases

====================================
PROBLEM CONTEXT (for outreach hooks)
====================================

**problem_statement**: What pain point does company solve? 1-2 sentences.
- Look for: "We're solving X", "Industry struggles with Y", customer problems
- If not found: "[RESEARCH NEEDED: Company problem statement from website/blog]"

**technical_challenge**: Core technical problem. 1 sentence.
- Look for: Architecture challenges, scale problems, integration complexity
- Example: "Orchestrating real-time data across external APIs with different failure modes"
- If not found: "[RESEARCH NEEDED: Technical challenge]"

**solution_approach**: How they solve it differently. 1 sentence.
- Look for: "Unlike competitors", "Our approach", unique architecture
- Example: "Built orchestration layer first (competitors bolt AI onto legacy systems)"
- If not found: "[RESEARCH NEEDED: Company approach/differentiation]"

**why_now**: Why urgent/timely. 1 sentence.
- Look for: Funding mentions, launch timeline, market timing
- Example: "Launching Q1 2025, 90-day architecture window before Series A"
- If not found: "[RESEARCH NEEDED: Timing/market window]"

====================================
CREDIBILITY SIGNALS (mostly research gaps)
====================================

**founder_background**: Founder background if mentioned.
- Look for: "Founded by", "CEO previously at"
- If not found: "[RESEARCH NEEDED: Founder LinkedIn]"

**team_pedigree**: Team backgrounds if mentioned.
- Look for: "Team from X, Y, Z", "Engineers previously at"
- Example: "Ex-Stripe, Plaid, Rippling engineers"
- If not found: "[RESEARCH NEEDED: Team LinkedIn profiles]"

**traction_metrics**: ARR, customers, growth if mentioned.
- Look for: Revenue, customer count, growth percentages
- Example: "$6M ARR, 900 customers, 500% YoY growth"
- If not found: "[RESEARCH NEEDED: Company blog/Crunchbase for traction]"

**customer_status**: Launch/customer status if mentioned.
- Example: "Early customers live, launching Q1 2025"
- If not found: "[RESEARCH NEEDED: Company blog/press for launch status]"

====================================
ROLE DETAILS
====================================

**core_responsibility**: Primary ownership. 1 sentence.
- Extract main responsibility from description
- Example: "Build orchestration layer for real-time financial data sync"

**day_to_day_tasks**: 3-5 specific tasks. Start with verbs.
- Extract tasks (not "collaborate with team" - be specific)
- Example: "Design fault-tolerant integrations with external APIs"
- Example: "Build workflow engine with rollback/retry logic"
- Example: "Own AWS infrastructure and observability stack"

**impact_statement**: Why role matters. 1 sentence.
- Infer from role level + company stage
- Example: "Your decisions = company's technical foundation" (early-stage)
- Example: "Direct impact on product performance at scale" (growth-stage)

====================================
REQUIREMENTS (from Detail API)
====================================

**must_haves**: Deal-breaker requirements. Format: "[Quantifier]: [Requirement (context)]"

Extract from requirements with priority "DEALBREAKER" or "REQUIRED":
- Add quantifiers (5+ years, 3+ years, expert-level)
- Add context in parentheses to clarify vague requirements
- Skip generic fluff ("strong communication", "team player")

Examples:
✅ "5+ years: Production distributed systems (APIs, fault tolerance)"
✅ "0→1 experience: Founding engineer or first 10 at startup"
✅ "NYC-based: In-person 3-5 days/week in Manhattan office"

**nice_to_haves**: Preferred requirements. Same format.

Extract from requirements with priority "NICE_TO_HAVE":
- Same format as must-haves

====================================
INTERVIEW PROCESS
====================================

**stages**: Stage descriptions.
- Look for interview process in description
- If not found, use template based on company stage (check funding/team size):
  - Early-stage: ["1. Founder/CTO technical (90min) - Architecture design", "2. Team fit (60min) - Real problem session", "3. Final (30min) - Equity/culture"]
  - Growth-stage: ["1. Recruiter screen (30min)", "2. Technical phone (60min) - Coding + design", "3. Onsite (4hrs)", "4. Final (30min)"]

**evaluation_criteria**: What they're evaluating. Format as questions.
- Infer from must-haves
- Example: "Can you design fault-tolerant systems? (not just implement features)"
- Example: "Have you shaped technical direction at 0→1 stage?"

**prep_needed**: What candidate should prep.
- Example: "Have ready 2-3 API integration projects with failure handling examples"
- Example: "Prepare system design stories focusing on reliability"

====================================
RED FLAGS
====================================

Analyze for concerning signals. Format: "[Signal] = [Risk interpretation]"

Examples:
✅ "90-day architecture window = High pressure, irreversible decisions"
✅ "Founding engineer at 45-person Series A = Title inflation"
✅ "Full-stack + infra + ML = Broad role, hard to go deep"
✅ "Hybrid 3-5 days = Less flexibility than remote"

Look for:
- Unrealistic timelines, vague descriptions, title inflation
- Scope creep (too many responsibilities)
- Concerning workplace signals

CRITICAL: Extract ONLY what's in description. Mark gaps with [RESEARCH NEEDED].""",
    )

    return agent


def _strip_html(html: str | None) -> str:
    """Strip HTML tags and clean up text."""
    if not html:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html)

    # Decode common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def _format_requirements(requirements: list[dict[str, Any]]) -> str:
    """Format requirements array for LLM prompt."""
    if not requirements:
        return "No structured requirements provided"

    formatted_lines = []
    for req in requirements:
        requirement_text = req.get("requirement", "")
        priority = req.get("priority", "")
        if requirement_text:
            formatted_lines.append(f"- {requirement_text} ({priority})")

    return "\n".join(formatted_lines) if formatted_lines else "No requirements"


def _format_questions(questions: list[dict[str, Any]]) -> str:
    """Format application questions for LLM prompt."""
    if not questions:
        return "No application questions"

    formatted_lines = []
    for i, q in enumerate(questions, 1):
        question_text = q.get("question", "")
        if question_text:
            formatted_lines.append(f"{i}. {question_text}")

    return "\n".join(formatted_lines) if formatted_lines else "No questions"


async def generate_profile(
    paraform_id: str,
    detail_response: dict[str, Any],
    meeting_data: dict[str, Any] | None,
) -> RoleProfile:
    """Generate company/role profile from detailed role data.

    Args:
        paraform_id: Role ID
        detail_response: Response from getRoleByIdDetailed
        meeting_data: Response from meetings.getAllIntakeAndOnboardingCallsByRoleId (unused in Phase 1)

    Returns:
        Structured role profile with [RESEARCH NEEDED] gaps

    Raises:
        TimeoutError: If LLM call exceeds 30 seconds
        RuntimeError: If extraction fails
    """
    logger.info("jobs.profile.extraction_started", paraform_id=paraform_id)

    # Note: meeting_data reserved for future use (e.g., responsiveness signals)
    _ = meeting_data

    # Extract detail fields
    detail = detail_response.get("result", {}).get("data", {}).get("json", {})
    description = detail.get("description", "")
    requirements = detail.get("requirements", [])
    experience_info = detail.get("experience_info", "")
    workplace_text = detail.get("workPlaceText", "")
    role_questions = detail.get("role_question", [])

    # Build context for LLM
    context = f"""
ROLE DESCRIPTION:
{_strip_html(description)}

REQUIREMENTS:
{_format_requirements(requirements)}

EXPERIENCE INFO:
{experience_info}

WORKPLACE:
{workplace_text}

APPLICATION QUESTIONS:
{_format_questions(role_questions)}
"""

    try:
        agent = _get_profile_agent()
        # CRITICAL: Timeout protection (ADR-002)
        result = await asyncio.wait_for(
            agent.run(f"Extract profile data for this role:\n\n{context}"), timeout=30.0
        )

        profile = result.output  # Use .output not .data (common mistake)

        logger.info(
            "jobs.profile.extraction_completed",
            paraform_id=paraform_id,
            must_haves_count=len(profile.must_haves),
            red_flags_count=len(profile.red_flags),
        )

        return profile

    except TimeoutError:
        logger.error(
            "jobs.profile.extraction_timeout",
            paraform_id=paraform_id,
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            "jobs.profile.extraction_failed",
            paraform_id=paraform_id,
            error=str(e),
            exc_info=True,
        )
        raise RuntimeError(f"Profile generation failed: {e}") from e
