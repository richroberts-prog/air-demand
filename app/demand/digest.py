"""Digest generation and sending for new and top roles."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.demand.email_builder import DigestEmailBuilder
from app.demand.email_service import send_digest_email
from app.demand.models import Role, UserSettings
from app.shared.constants import TIER_1_INVESTORS, TIER_2_INVESTORS

logger = get_logger(__name__)


def get_session_expiry() -> datetime | None:
    """Get Paraform session expiry from session file.

    Returns:
        Expiry datetime if session file exists and has valid token, None otherwise.
    """
    session_path = Path("paraform_session.json")
    if not session_path.exists():
        return None

    try:
        with session_path.open() as f:
            session_data = json.load(f)

        # Find the session token cookie
        for cookie in session_data.get("cookies", []):
            if cookie.get("name") == "__Secure-next-auth.session-token":
                expires = cookie.get("expires")
                if expires and expires > 0:  # -1 means session cookie
                    return datetime.fromtimestamp(expires, tz=UTC)

        return None
    except Exception as e:
        logger.warning("jobs.digest.session_expiry_check_failed", error=str(e))
        return None


async def generate_and_send_digest() -> bool:
    """Generate and send a digest email with new and top roles.

    Queries roles that appeared since the last digest and top qualified roles.
    Formats an email and sends it via the email service.
    Updates last_digest_sent_at timestamp on success.

    Returns:
        True if digest was generated and sent successfully, False otherwise.
    """
    logger.info("jobs.digest.generation_started")

    async with get_db_session() as session:
        # Get or create user settings
        result = await session.execute(select(UserSettings).where(UserSettings.id == 1))
        user_settings = result.scalar_one_or_none()

        if user_settings is None:
            user_settings = UserSettings(id=1)
            session.add(user_settings)

        # Always look at last 24 hours for market intelligence
        since = datetime.now(UTC) - timedelta(hours=24)

        logger.info("jobs.digest.query_params", since=since.isoformat())

        # Query ALL roles posted on Paraform in last 24 hours
        # No tier filtering - show QUALIFIED, MAYBE, and SKIP for market intel + QC
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        posted_at_text = Role.raw_response["posted_at"].astext
        posted_at_ts = cast(posted_at_text, TIMESTAMP(timezone=True))

        roles_stmt = (
            select(Role)
            .where(posted_at_ts > since)
            .where(Role.lifecycle_status == "ACTIVE")
            .order_by(Role.combined_score.desc().nulls_last())
            # No limit - show all roles from yesterday
        )
        roles_result = await session.execute(roles_stmt)
        roles = list(roles_result.scalars().all())

        logger.info(
            "jobs.digest.roles_queried",
            total_count=len(roles),
        )

        # Prepare template context
        from app.core.config import get_settings

        settings = get_settings()
        context = {
            "roles": roles,
            "since": since,
            "until": datetime.now(UTC),
            "total_count": len(roles),
            "tier_1_investors": set(TIER_1_INVESTORS),
            "tier_2_investors": set(TIER_2_INVESTORS),
            "session_expiry": get_session_expiry(),
            "dashboard_url": settings.dashboard_url,
        }

        # Build email content from templates
        template_dir = Path(__file__).parent / "templates"
        builder = DigestEmailBuilder(template_dir)
        html_body = builder.build_html(context)
        text_body = builder.build_text(context)

        # Generate email content with role count
        date_str = datetime.now(UTC).strftime("%b %d")
        role_count = len(roles)
        subject = f"AI Recruiter Digest - {role_count} roles posted yesterday ({date_str})"

        # Send email
        sent = send_digest_email(subject, html_body, text_body)

        if sent:
            # Update last digest sent timestamp
            user_settings.last_digest_sent_at = datetime.now(UTC)
            await session.commit()
            logger.info("jobs.digest.generation_completed", sent=True)
            return True
        else:
            logger.warning("jobs.digest.generation_completed", sent=False)
            return False
