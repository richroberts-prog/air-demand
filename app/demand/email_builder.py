"""Email template builder using Jinja2 templates for digest emails."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.logging import get_logger
from app.shared.constants import get_investor_short_name, normalize_investor_name
from app.shared.formatting import (
    format_date_iso,
    format_date_short,
    format_funding_amount,
    format_funding_stage,
    format_hiring_count,
    format_industry,
    format_location,
    format_percent_fee,
    format_role_type,
    format_salary,
    format_score,
    get_disqualification_category,
)

logger = get_logger(__name__)


class DigestEmailBuilder:
    """Builds digest emails from Jinja2 templates with custom filters."""

    def __init__(self, template_dir: Path) -> None:
        """Initialize the email builder with Jinja2 environment.

        Args:
            template_dir: Path to directory containing Jinja2 templates
        """
        self.template_dir = template_dir
        logger.info("email_builder.initialization_started", template_dir=str(template_dir))

        try:
            # Initialize Jinja2 environment
            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(["html", "xml"]),
            )

            # Register custom filters from shared/formatting
            self.env.filters["format_salary"] = format_salary
            self.env.filters["format_funding"] = format_funding_amount
            self.env.filters["format_date"] = format_date_iso
            self.env.filters["format_date_short"] = format_date_short
            self.env.filters["format_score"] = format_score
            self.env.filters["format_stage"] = format_funding_stage
            self.env.filters["format_industry"] = format_industry
            self.env.filters["format_role_type"] = self._format_role_type_filter
            self.env.filters["format_location"] = self._format_location_filter
            self.env.filters["format_hiring"] = format_hiring_count
            self.env.filters["format_fee"] = format_percent_fee
            self.env.filters["get_investor_short"] = get_investor_short_name
            self.env.filters["normalize_investor"] = normalize_investor_name
            self.env.filters["dq_category"] = get_disqualification_category

            logger.info("email_builder.initialization_completed", filters_count=14)

        except Exception as e:
            logger.error(
                "email_builder.initialization_failed",
                exc_info=True,
                error=str(e),
                template_dir=str(template_dir),
            )
            raise

    def _format_role_type_filter(self, role_types: list[str]) -> str:
        """Jinja2 filter for role type formatting.

        Args:
            role_types: List of role type identifiers

        Returns:
            Formatted role type display name
        """
        return format_role_type(role_types) if role_types else "—"

    def _format_location_filter(
        self, locations: list[str], workplace_type: str | None = None
    ) -> str:
        """Jinja2 filter for location formatting.

        For email digest, show compact location (max 1 location).

        Args:
            locations: List of location identifiers
            workplace_type: Workplace type (Remote, Hybrid, On-site)

        Returns:
            Formatted location display string (e.g., "NYC", "Remote", "SF (Remote)")
        """
        return format_location(locations, workplace_type, max_locations=1)

    def build_html(self, context: dict[str, Any]) -> str:
        """Render HTML email template.

        Args:
            context: Template context with roles, dates, and constants

        Returns:
            Rendered HTML email content

        Raises:
            Exception: If template rendering fails
        """
        logger.info("email_builder.html_rendering_started")

        try:
            template = self.env.get_template("digest.html.jinja2")
            html_body = template.render(**context)
            logger.info("email_builder.html_rendering_completed", body_length=len(html_body))
            return html_body

        except Exception as e:
            logger.error(
                "email_builder.html_rendering_failed",
                exc_info=True,
                error=str(e),
            )
            raise

    def build_text(self, context: dict[str, Any]) -> str:
        """Render plain text email template.

        Args:
            context: Template context with roles, dates, and constants

        Returns:
            Rendered plain text email content

        Raises:
            Exception: If template rendering fails
        """
        logger.info("email_builder.text_rendering_started")

        try:
            template = self.env.get_template("digest.txt.jinja2")
            text_body = template.render(**context)
            logger.info("email_builder.text_rendering_completed", body_length=len(text_body))
            return text_body

        except Exception as e:
            logger.error(
                "email_builder.text_rendering_failed",
                exc_info=True,
                error=str(e),
            )
            raise
