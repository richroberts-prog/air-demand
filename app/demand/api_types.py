"""TypedDict definitions for Paraform tRPC API responses.

These types document the structure of raw API responses stored in `raw_response` JSONB.
Use these for type checking when accessing fields from the API response.

Endpoints covered:
- activeRoles.searchActiveRoles (Browse API)
- role.getRoleByIdDetailed (Detail API)
- meetings.getAllIntakeAndOnboardingCallsByRoleId
- meetings.getMeetingById
"""

from typing import Any, NotRequired, TypedDict

# ====================
# Company Types
# ====================


class CompanyMetadata(TypedDict, total=False):
    """Nested company metadata from Browse API."""

    last_funding_round: str  # e.g., "SERIES_A", "SEED"
    paraform_owner: dict[str, Any]  # {id, name, image} - account manager


class Company(TypedDict, total=False):
    """Company object nested in role response."""

    # Always present
    name: str

    # Usually present
    logoUrl: str | None
    industries: list[str]  # e.g., ["ai", "creator_economy"]
    size: int | None  # Team size
    foundingYear: int | None
    websiteUrl: str | None
    oneLiner: str | None  # Short company description

    # Funding
    fundingAmount: str | None  # e.g., "$16.25M"

    # Nested
    company_metadata: CompanyMetadata

    # Detail API only
    description: str | None  # HTML - full company description
    team_image_url: str | None


# ====================
# Role Metadata Types
# ====================


class RoleMetadata(TypedDict, total=False):
    """Nested role metadata from Browse API."""

    highlights: list[str]  # e.g., ["NO_FINAL_ROUNDS", "HIRING_MULTIPLE", "TRUSTED_CLIENT"]
    posted_at: str  # ISO datetime
    ai_role_titles: list[str]  # AI-generated alternative titles


class RoleBoost(TypedDict, total=False):
    """Bonus opportunity for a role."""

    id: str
    num_activations: int
    start_date: str  # ISO datetime
    end_date: str  # ISO datetime
    application_status: str  # e.g., "INTERVIEWING"
    bonus_amount: int  # e.g., 1800 (USD)
    a_b_test_enabled: bool
    invite_only: bool


class RoleSettings(TypedDict, total=False):
    """Role-specific settings."""

    max_pending_submissions: int
    first_submission_reward_enabled: bool
    first_submission_reward_amount: int
    role_timer_enabled: bool


# ====================
# Requirement Types (Detail API)
# ====================


class Requirement(TypedDict):
    """Structured requirement from Detail API."""

    type: str  # "DEALBREAKER", "REQUIRED", "NICE_TO_HAVE"
    group: str  # "HARD_SKILLS", "SOFT_SKILLS", "WORK_EXPERIENCE", "EDUCATION"
    description: str
    active: bool


# ====================
# Browse API Response
# ====================


class BrowseRoleResponse(TypedDict, total=False):
    """Single role from activeRoles.searchActiveRoles response.

    This is the primary type for raw_response JSONB storage.
    Not all fields are always present - use .get() with defaults.
    """

    # === Core Role Fields ===
    id: str  # Paraform role ID (stored as paraform_id)
    name: str  # Role title
    status: str  # "ACTIVE", "CLOSED", etc.
    createdAt: str  # ISO datetime
    posted_at: str  # ISO datetime
    is_posted_recently: bool
    priority: int  # Paraform's internal priority score

    # === Company (nested) ===
    company: Company

    # === Investors ===
    investors: list[str]  # e.g., ["Benchmark", "Craft Ventures", "a16z"]

    # === Compensation ===
    salary_string: str | None  # e.g., "$150K - $225K"
    salary_number: int | None  # Lower bound number
    salaryLowerBound: int | None  # e.g., 150000
    salaryUpperBound: int | None  # e.g., 225000
    currencyType: str  # e.g., "USD"
    equity: str | None  # e.g., "Competitive", "0.1% - 0.5%"
    base_bounty: int | None
    bounty: int | None
    bounty_string: str | None  # e.g., "17.5% first year"
    percent_fee: float | None  # Commission percentage, e.g., 17.5
    retainer: bool
    weekly_retainer: bool
    visa_text: str | None  # e.g., "Not available"

    # === Experience Requirements ===
    yoe_string: str | None  # e.g., "3 - 10 years"
    yoe_min: str | None  # e.g., "3"
    yoe_max: str | None  # e.g., "10"
    yoe_experience: str | None  # e.g., "4-7"
    tech_stack: list[str]  # e.g., ["react", "python", "postgresql"]
    role_types: list[str]  # e.g., ["full_stack_engineer", "backend_engineer"]

    # === Location & Remote ===
    locations: list[str]  # e.g., ["new_york", "remote"]
    workplace_type: str | None  # "Remote", "Hybrid", "On-site"

    # === Hiring Metrics ===
    hiring_count: int | None  # Positions available
    hiring_count_max: int | None
    hiring_count_text: str | None  # e.g., "10+"
    team_size: int | None  # Team the role reports into
    experience_count: int | None  # Number of applications (competition)

    # === Pipeline Metrics ===
    submitted: int | None  # Your submissions
    total_interviewing: int | None  # Total candidates interviewing
    total_hired: int | None  # Total placements made
    interviewing: int | None  # Your candidates interviewing
    hired: int | None  # Your placements
    approved_recruiters_count: int | None  # Competition level

    # === Quality Signals ===
    manager_rating: int | None  # 1-5 stars
    responsiveness_days: float | None  # e.g., 0.049 = responds in ~1 hour
    interview_stages: int | None  # Number of interview rounds
    manager_last_active: str | None  # ISO datetime

    # === Metadata (nested) ===
    role_metadata: NotRequired[RoleMetadata]
    role_boost: NotRequired[RoleBoost]
    role_settings: NotRequired[RoleSettings]

    # === Recruiter Access ===
    not_accepting_recruiters: bool
    hide_from_recruiters: bool
    applied_for_role: bool
    user_status: str | None  # e.g., "WITHDRAWN", "APPROVED"
    allow_custom_rate: bool
    max_capacity: bool

    # === Paraform Owner (nested) ===
    paraform_owner: NotRequired[dict[str, Any]]  # {id, name, image}


# ====================
# Detail API Response
# ====================


class DetailRoleResponse(BrowseRoleResponse, total=False):
    """Extended role from role.getRoleByIdDetailed response.

    Includes all Browse API fields plus additional detail fields.
    """

    # === Detail-only fields ===
    description: str | None  # HTML - full role description
    requirements: list[Requirement]  # Structured requirements
    experience_info: str | None  # Additional experience requirements
    workPlaceText: str | None  # e.g., "In-person 5 days/week in NYC"
    role_question: list[dict[str, Any]]  # Application questions


# ====================
# Meeting Types
# ====================


class IntakeCall(TypedDict, total=False):
    """Intake call meeting from meetings.getAllIntakeAndOnboardingCallsByRoleId."""

    id: str  # Meeting ID
    # Other fields TBD based on actual response


class MeetingTranscript(TypedDict, total=False):
    """Meeting with transcript from meetings.getMeetingById."""

    id: str
    transcription: str | None  # HTML transcript content
    # Other fields TBD based on actual response


# ====================
# tRPC Response Wrappers
# ====================


class TRPCResult(TypedDict):
    """Standard tRPC response wrapper."""

    data: dict[str, Any]  # Contains {json: ...actual data...}


class TRPCResponse(TypedDict):
    """Standard tRPC response."""

    result: TRPCResult
