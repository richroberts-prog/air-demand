"""Pydantic schemas for jobs feature v0.1 - simplified for JSONB storage."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.formatting import (
    format_date_short,
    format_funding_amount,
    format_funding_stage,
    format_hiring_count,
    format_industry,
    format_location,
    format_manager_active,
    format_percent_fee,
    format_remaining_positions,
    format_role_type,
    format_salary,
    format_score,
)

if TYPE_CHECKING:
    from app.demand.models import Role

# ====================
# Role Schemas (v0.1)
# ====================


class RoleResponse(BaseModel):
    """Schema for role responses.

    All role data lives in raw_response. This schema exposes:
    - Core fields for API responses
    - Qualification status
    - Convenience accessors for common fields
    """

    id: int
    paraform_id: str

    # Raw tRPC response - all the data
    raw_response: dict[str, Any]

    # Qualification
    is_qualified: bool
    qualification_tier: str | None  # QUALIFIED, MAYBE, SKIP
    qualification_reasons: list[str]
    disqualification_reasons: list[str]

    # Lifecycle
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    # Convenience fields (extracted from raw_response for easy access)
    @property
    def title(self) -> str:
        """Role title."""
        return str(self.raw_response.get("name", "Unknown"))

    @property
    def company_name(self) -> str:
        """Company name."""
        company = self.raw_response.get("company", {})
        return str(company.get("name", "Unknown"))

    @property
    def salary_range(self) -> str:
        """Formatted salary range (per ADR-003: upper bound only in 225K format)."""
        lower = self.raw_response.get("salaryLowerBound")
        upper = self.raw_response.get("salaryUpperBound")
        return format_salary(lower, upper)

    @property
    def paraform_url(self) -> str:
        """URL to this role on Paraform."""
        company_slug = self.company_name.lower().replace(" ", "-")
        return f"https://www.paraform.com/company/{company_slug}/{self.paraform_id}"

    model_config = ConfigDict(from_attributes=True)


class RoleListItem(BaseModel):
    """Lightweight role for list views.

    Extracts key fields from raw_response for display in tables/lists.
    """

    id: int
    paraform_id: str
    qualification_tier: str | None
    qualification_reasons: list[str]  # Quality signals met (for QUALIFIED/MAYBE)
    disqualification_reasons: list[str]  # Why disqualified (for SKIP, for QC)
    first_seen_at: datetime

    # Raw values (for compatibility)
    title: str
    company_name: str
    company_logo_url: str | None
    salary_lower: int | None
    salary_upper: int | None
    salary_string: str | None
    locations: list[str]
    workplace_type: str | None
    role_types: list[str]
    qualifying_core_type: str | None
    tech_stack: list[str]
    hiring_count: int | None
    percent_fee: float | None
    manager_rating: float | None
    investors: list[str]
    highlights: list[str]
    funding_amount: str | None
    funding_stage: str | None
    company_size: int | None
    paraform_url: str
    total_interviewing: int | None
    total_hired: int | None
    interview_stages: int | None
    responsiveness_days: float | None
    manager_last_active: str | None
    approved_recruiters_count: int | None
    yoe_string: str | None
    one_liner: str | None
    priority: int | None
    posted_at: str | None
    industries: list[str]
    industry: str
    founding_year: int | None
    engineer_score: float | None
    headhunter_score: float | None
    excitement_score: float | None
    combined_score: float | None
    has_briefing: bool = False  # Whether briefing exists for this role
    trend: str | None = None
    extracted_location: str | None = None
    location_confidence: str | None = None

    # Formatted display fields (single source of truth for rendering)
    salary_display: str  # "225"
    funding_display: str  # "11" (integer millions)
    funding_stage_display: str  # "A", "Seed"
    role_type_display: str  # "Backend", "Full Stack"
    location_display: str  # "NYC", "SF", "Remote"
    workplace_display: str  # "Remote", "Hybrid", "On-site"
    yoe_display: str  # "3-7", "5+"
    posted_at_display: str  # "12-09" (MM-DD)
    hiring_count_display: str  # "5", "100" (total positions)
    remaining_positions_display: str  # "5", "83" (after subtracting hired)
    percent_fee_display: str  # "15.5"
    engineer_score_display: str  # "85"
    headhunter_score_display: str  # "92"
    excitement_score_display: str  # "78"
    combined_score_display: str  # "85"
    manager_active_display: str  # "Today", "1d", "3d", "2w", "3mo"

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_role(cls, role: "Role") -> "RoleListItem":
        """Create from Role model instance."""
        raw = role.raw_response
        company = raw.get("company", {})
        company_meta = company.get("company_metadata", {})
        role_meta = raw.get("role_metadata", {})

        # Determine which core type qualified this role
        role_types = raw.get("role_types", [])
        qualifying_core_type = None
        core_types = {
            "backend_engineer",
            "full_stack_engineer",
            "embedded_firmware_engineer",
            "electrical_engineer",
            "mechanical_engineer",
            "forward_deployed_engineer_solutions_support",
        }
        for rt in role_types:
            if rt.lower() in core_types:
                qualifying_core_type = rt
                break

        # Include extracted location from enrichment data if present
        enrichment_data = raw.get("_enrichment", {}).get("extracted_data", {})
        extracted_location = enrichment_data.get("extracted_location")
        location_confidence = enrichment_data.get("location_confidence")

        # Extract raw values
        salary_lower = raw.get("salaryLowerBound")
        salary_upper = raw.get("salaryUpperBound")
        locations = raw.get("locations", [])
        workplace_type = raw.get("workplace_type")
        role_types_list = raw.get("role_types", [])
        funding_amount = company.get("fundingAmount")
        funding_stage = company_meta.get("last_funding_round")
        yoe_string = raw.get("yoe_string")
        posted_at = raw.get("posted_at")
        hiring_count = raw.get("hiring_count")
        percent_fee = raw.get("percent_fee")

        return cls(
            id=role.id,
            paraform_id=role.paraform_id,
            qualification_tier=role.qualification_tier,
            qualification_reasons=role.qualification_reasons or [],
            disqualification_reasons=role.disqualification_reasons or [],
            first_seen_at=role.first_seen_at,
            # Raw values
            title=raw.get("name", "Unknown"),
            company_name=company.get("name", "Unknown"),
            company_logo_url=company.get("logoUrl"),
            salary_lower=salary_lower,
            salary_upper=salary_upper,
            salary_string=raw.get("salary_string"),
            locations=locations,
            workplace_type=workplace_type,
            role_types=role_types_list,
            qualifying_core_type=qualifying_core_type,
            tech_stack=raw.get("tech_stack", []),
            hiring_count=hiring_count,
            percent_fee=percent_fee,
            manager_rating=raw.get("manager_rating"),
            investors=raw.get("investors", []),
            highlights=role_meta.get("highlights", []),
            funding_amount=funding_amount,
            funding_stage=funding_stage,
            company_size=company.get("size"),
            paraform_url=role.paraform_url,
            total_interviewing=raw.get("total_interviewing"),
            total_hired=raw.get("total_hired"),
            interview_stages=raw.get("interview_stages"),
            responsiveness_days=raw.get("responsiveness_days"),
            manager_last_active=raw.get("manager_last_active"),
            approved_recruiters_count=raw.get("approved_recruiters_count"),
            yoe_string=yoe_string,
            one_liner=raw.get("one_liner"),
            priority=raw.get("priority"),
            posted_at=posted_at,
            industries=company.get("industries", []),
            industry=format_industry(company.get("industries", [])),
            founding_year=company.get("foundingYear"),
            engineer_score=role.engineer_score,
            headhunter_score=role.headhunter_score,
            excitement_score=role.excitement_score,
            combined_score=role.combined_score,
            has_briefing=False,  # Set in routes after querying briefings
            extracted_location=extracted_location,
            location_confidence=location_confidence,
            # Formatted display fields (single source of truth)
            salary_display=format_salary(salary_lower, salary_upper),
            funding_display=format_funding_amount(funding_amount),
            funding_stage_display=format_funding_stage(funding_stage),
            role_type_display=format_role_type(
                [qualifying_core_type] if qualifying_core_type else role_types_list
            ),
            location_display=format_location(locations, workplace_type, max_locations=1),
            workplace_display=workplace_type or "On-site",
            yoe_display=_format_yoe(yoe_string),
            posted_at_display=format_date_short(posted_at),
            hiring_count_display=format_hiring_count(hiring_count),
            remaining_positions_display=format_remaining_positions(
                hiring_count, raw.get("total_hired")
            ),
            percent_fee_display=format_percent_fee(percent_fee),
            engineer_score_display=format_score(role.engineer_score),
            headhunter_score_display=format_score(role.headhunter_score),
            excitement_score_display=format_score(role.excitement_score),
            combined_score_display=format_score(role.combined_score),
            manager_active_display=format_manager_active(raw.get("manager_last_active")),
        )


def _format_yoe(yoe: str | None) -> str:
    """Format YOE to be concise: '3 - 7 years' -> '3-7', '5+ years' -> '5+'."""
    if not yoe:
        return "—"
    # Remove "years" and extra spaces
    clean = yoe.replace(" years", "").replace(" year", "").strip()
    # Convert "X - Y" to "X-Y"
    clean = clean.replace(" - ", "-")
    return clean or "—"


class RoleDetail(RoleListItem):
    """Full role detail for single role view.

    Extends RoleListItem with additional fields.
    """

    # Additional detail fields (not in RoleListItem)
    equity: str | None
    visa_text: str | None
    company_website: str | None

    # Score breakdown for explainability
    score_breakdown: dict[str, Any] | None

    # Full raw response for debugging/advanced use
    raw_response: dict[str, Any]

    @classmethod
    def from_role(cls, role: "Role") -> "RoleDetail":
        """Create from Role model instance."""
        # Reuse base extraction from parent
        base = RoleListItem.from_role(role)
        raw = role.raw_response
        company = raw.get("company", {})

        return cls(
            **base.model_dump(),
            # Detail fields only (not already in base)
            equity=raw.get("equity"),
            visa_text=raw.get("visa_text"),
            company_website=company.get("websiteUrl"),
            score_breakdown=role.score_breakdown,
            raw_response=raw,
        )


# ====================
# Scrape Run Schemas
# ====================


class ScrapeRunResponse(BaseModel):
    """Schema for scrape run responses."""

    id: int
    run_id: UUID
    status: str
    roles_found: int
    new_roles: int
    updated_roles: int
    qualified_roles: int
    errors: list[str]
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    triggered_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ====================
# Stats Schemas
# ====================


class QualificationStats(BaseModel):
    """Statistics about role qualification."""

    total_roles: int
    qualified_count: int
    maybe_count: int
    skip_count: int
    qualified_percentage: float


class RoleListResponse(BaseModel):
    """Paginated list of roles."""

    roles: list[RoleListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


# ====================
# Temporal Tracking Schemas
# ====================


class RoleChangeResponse(BaseModel):
    """Schema for role change records."""

    id: int
    role_id: int
    role_title: str
    company_name: str
    change_type: str
    field_name: str
    old_value: str | None
    new_value: str | None
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NewRolesResponse(BaseModel):
    """Response for new roles query."""

    roles: list[RoleListItem]
    count: int
    since: datetime


class RoleHistoryResponse(BaseModel):
    """Role with its change history."""

    role: RoleListItem
    changes: list[RoleChangeResponse]
    snapshots_count: int


# ====================
# User Settings Schemas
# ====================


class LastVisitResponse(BaseModel):
    """Response for last visit query."""

    last_visit: datetime | None
    updated_at: datetime | None


class LastVisitUpdate(BaseModel):
    """Request to update last visit timestamp."""

    last_visit: datetime


class BriefingHeaderMetadata(BaseModel):
    """Header metadata from Browse API (not in profile)."""

    company_name: str
    company_stage: str | None
    team_size: int | None
    salary_range: str  # e.g., "$120-260K"
    equity: str | None
    location: str
    workplace_type: str | None
    hiring_count: int | None
    interview_stages_count: int | None
    commission_percent: float | None
    commission_amount: str | None  # e.g., "$19-41K"


class ProblemContextSchema(BaseModel):
    """Problem/solution context for outreach hooks."""

    problem_statement: str | None
    technical_challenge: str | None
    solution_approach: str | None
    why_now: str | None


class CredibilitySignalsSchema(BaseModel):
    """Credibility signals (team, funding, traction)."""

    founder_background: str | None
    team_pedigree: str | None
    traction_metrics: str | None
    customer_status: str | None


class RoleDetailsSchema(BaseModel):
    """Role details (responsibility, day-to-day, impact)."""

    core_responsibility: str
    day_to_day_tasks: list[str]
    impact_statement: str | None


class InterviewProcessSchema(BaseModel):
    """Interview process and prep intel."""

    stages: list[str]
    evaluation_criteria: list[str]
    prep_needed: list[str]


class RoleBriefingResponse(BaseModel):
    """Complete briefing with header + profile sections."""

    paraform_id: str

    # Header (from Browse API)
    header: BriefingHeaderMetadata

    # Profile sections (from LLM extraction)
    problem: ProblemContextSchema
    credibility: CredibilitySignalsSchema
    role: RoleDetailsSchema
    must_haves: list[str]
    nice_to_haves: list[str]
    interview: InterviewProcessSchema
    red_flags: list[str]

    # Metadata
    score_at_enrichment: float
    enriched_at: datetime

    model_config = ConfigDict(from_attributes=True)
