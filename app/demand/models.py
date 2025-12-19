"""Database models for jobs/demand side (Paraform roles) - v0.1 Clean Slate.

This is a simplified schema that stores the full tRPC response as JSONB,
with qualification computed from that data.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class Role(Base, TimestampMixin):
    """Job role from Paraform with raw tRPC response and qualification status.

    All role data lives in raw_response JSONB. Qualification is computed
    from that data using hard filters and quality signals.
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    paraform_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # Raw tRPC response - the full Browse API response for this role
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Content hash for change detection (SHA256 of meaningful fields)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # Qualification (computed from raw_response)
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    qualification_tier: Mapped[str | None] = mapped_column(
        String(20), index=True
    )  # QUALIFIED, MAYBE, SKIP
    qualification_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    disqualification_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )

    # Lifecycle
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Lifecycle status tracking
    lifecycle_status: Mapped[str] = mapped_column(
        String(20), default="ACTIVE", nullable=False, index=True
    )  # ACTIVE, FILLED, REMOVED, PAUSED
    last_seen_in_scrape_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("role_scrape_runs.id"), nullable=True
    )
    disappeared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Scores (0.00-1.00)
    engineer_score: Mapped[float | None] = mapped_column(Float, index=True)
    headhunter_score: Mapped[float | None] = mapped_column(Float, index=True)
    excitement_score: Mapped[float | None] = mapped_column(Float)
    combined_score: Mapped[float | None] = mapped_column(Float, index=True)  # Weighted combo

    # Score explainability (JSONB for detailed breakdown)
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Convenience properties for common raw_response fields
    @property
    def title(self) -> str:
        """Role title from raw response."""
        return str(self.raw_response.get("name", "Unknown"))

    @property
    def company_name(self) -> str:
        """Company name from raw response."""
        company = self.raw_response.get("company", {})
        return str(company.get("name", "Unknown"))

    @property
    def salary_upper(self) -> int | None:
        """Upper salary bound from raw response."""
        return self.raw_response.get("salaryUpperBound")

    @property
    def salary_lower(self) -> int | None:
        """Lower salary bound from raw response."""
        return self.raw_response.get("salaryLowerBound")

    @property
    def role_types(self) -> list[str]:
        """Role types from raw response (Paraform taxonomy)."""
        result: list[str] = self.raw_response.get("role_types", [])
        return result

    @property
    def locations(self) -> list[str]:
        """Locations from raw response."""
        result: list[str] = self.raw_response.get("locations", [])
        return result

    @property
    def workplace_type(self) -> str | None:
        """Workplace type (Remote, Hybrid, On-site) from raw response."""
        return self.raw_response.get("workplace_type")

    @property
    def paraform_url(self) -> str:
        """URL to this role on Paraform."""
        company_slug = self.company_name.lower().replace(" ", "-")
        return f"https://www.paraform.com/company/{company_slug}/{self.paraform_id}"


class RoleScrapeRun(Base, TimestampMixin):
    """Execution tracking for Paraform scraping runs."""

    __tablename__ = "role_scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(unique=True, nullable=False, default=uuid4, index=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'running', 'completed', 'failed'

    # Results
    roles_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_roles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_roles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qualified_roles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_unchanged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Errors (JSON array of error objects)
    errors: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Metadata
    triggered_by: Mapped[str | None] = mapped_column(String(50))  # 'scheduler', 'manual', 'api'


class CompanyEnrichment(Base, TimestampMixin):
    """LLM-generated company excitement assessment, cached per company.

    Used to enhance scoring for companies where algorithmic signals
    are insufficient (0.50-0.70 score range).
    """

    __tablename__ = "company_enrichments"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Company identifier (normalized lowercase, unique)
    company_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # LLM assessment results
    excitement_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    signals: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    # Metadata for cache invalidation
    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "gemini-2.0-flash"

    # Optional: raw context used for enrichment (for debugging)
    context_used: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class RoleEnrichment(Base, TimestampMixin):
    """LLM-extracted intel from role HTML fields (companyTip, selling_points).

    Extracts all useful scoring signals not available in structured API data:
    - Investors (VCs)
    - Notable advisors/angels
    - Founder background
    - Company stage signals
    - Process speed indicators
    - Risk/runway signals

    Cached per role, not re-extracted on subsequent scrapes.
    """

    __tablename__ = "role_enrichments"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Role identifier (one enrichment per role)
    paraform_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # Extracted structured data (JSONB for flexibility)
    # Contains: investors, angels, advisors, funding_stage, founder_background,
    #           company_stage, process_signals, risk_signals, key_highlights
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Scoring signals (list of strings for quick lookup)
    positive_signals: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    negative_signals: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    # Convenience fields for common lookups
    investors: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    funding_stage: Mapped[str | None] = mapped_column(String(50))

    # Location extraction (Phase 15b)
    extracted_location: Mapped[str | None] = mapped_column(String(100))
    extracted_location_confidence: Mapped[str | None] = mapped_column(String(20))

    # Source text used for extraction (for debugging)
    source_company_tip: Mapped[str | None] = mapped_column(Text)
    source_selling_points: Mapped[str | None] = mapped_column(Text)

    # Metadata
    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)


class RoleBriefing(Base, TimestampMixin):
    """Company/role profile for outreach generation (Phase 1: Paraform + LLM extraction).

    Profile data used to GENERATE outreach messages and briefings.
    Header metadata (company, compensation, commission) injected from Browse API at presentation layer.
    """

    __tablename__ = "role_briefings"

    id: Mapped[int] = mapped_column(primary_key=True)
    paraform_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # Raw source data (Bronze layer)
    detail_raw_response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    meeting_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Structured profile data (Silver layer) - stored as JSONB for flexibility
    profile_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Structure: {
    #   "problem": {...},
    #   "credibility": {...},
    #   "role": {...},
    #   "must_haves": [...],
    #   "nice_to_haves": [...],
    #   "interview": {...},
    #   "red_flags": [...]
    # }

    # OLD FIELDS (deprecated - will be removed after migration validation)
    # LLM-generated briefing fields
    pitch_summary: Mapped[str] = mapped_column(Text, nullable=False)  # 2-3 sentence pitch
    key_selling_points: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False
    )  # Why top engineers care

    # Role details (extracted from description HTML)
    day_to_day: Mapped[str | None] = mapped_column(Text)  # What they'll actually do
    requirements_must_have: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    requirements_nice_to_have: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Interview intel
    interview_stages: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    interview_timeline: Mapped[str | None] = mapped_column(String(100))  # "2-3 weeks"
    interview_prep_notes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Application prep
    application_questions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    info_to_gather: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )  # Pre-submission checklist

    # Red flags
    red_flags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Metadata
    score_at_enrichment: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # Combined score when briefing created
    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)


class RoleSnapshot(Base, TimestampMixin):
    """Point-in-time snapshot of role data per scrape run.

    Stores full raw_response for each role at each scrape, enabling:
    - Complete audit trail of role changes over time
    - Diffing between any two points in time
    - Detecting what changed between scrapes
    """

    __tablename__ = "role_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scrape_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role_scrape_runs.id"), nullable=False, index=True
    )

    # Full raw response at this point in time
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Key fields extracted for efficient querying (avoid JSONB parsing)
    salary_upper: Mapped[int | None] = mapped_column(Integer)
    percent_fee: Mapped[float | None] = mapped_column(Float)
    hiring_count: Mapped[int | None] = mapped_column(Integer)

    # Timestamp of when this snapshot was taken
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class RoleChange(Base, TimestampMixin):
    """Detected change in role between scrapes.

    Records specific field changes for easy querying and display.
    Change types: SALARY_INCREASE, SALARY_DECREASE, FEE_CHANGE, HEADCOUNT_CHANGE,
                  LOCATION_CHANGE, STATUS_CHANGE, COMPETITION_CHANGE, REAPPEARED, DISAPPEARED
    """

    __tablename__ = "role_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scrape_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role_scrape_runs.id"), nullable=False, index=True
    )

    # What changed
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)

    # When detected
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class UserSettings(Base, TimestampMixin):
    """User settings for the dashboard (single-user app).

    Stores persistent settings like last_visit timestamp for the What's New page.
    Only one row expected (id=1).
    """

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    last_dashboard_visit: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_digest_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
