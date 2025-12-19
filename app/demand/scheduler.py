"""APScheduler runner for automated scraping and digest jobs."""

import asyncio

# Import monitoring script
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from apscheduler.schedulers.asyncio import (  # type: ignore[import-untyped]
    AsyncIOScheduler,
)
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.logging import get_logger, setup_logging
from app.core.monitoring import ErrorAggregator, get_error_aggregator
from app.demand.digest import generate_and_send_digest
from app.demand.email_service import send_digest_email
from app.demand.scraper.orchestrator import run_scrape

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.monitor_openrouter_models import main as monitor_openrouter_main

logger = get_logger(__name__)


async def scrape_job() -> None:
    """Execute scrape job with error monitoring."""
    error_aggregator = get_error_aggregator()
    logger.info("jobs.scheduler.scrape_started")
    start_time = datetime.now(UTC)

    try:
        async with get_db_session() as db:
            result = await run_scrape(db, triggered_by="scheduler")
            await db.commit()
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(
                "jobs.scheduler.scrape_completed",
                run_id=str(result.run_id),
                roles_found=result.roles_found,
                new_roles=result.new_roles,
                duration_seconds=round(duration, 1),
            )
    except Exception as e:
        duration = (datetime.now(UTC) - start_time).total_seconds()
        logger.error(
            "jobs.scheduler.scrape_failed",
            error=str(e),
            duration_seconds=round(duration, 1),
            exc_info=True,
        )
        # Record error for aggregation
        error_aggregator.record_error(
            "scrape_failed",
            {
                "error": str(e),
                "duration_seconds": duration,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        # Check if we should send alert
        await _check_and_send_alert(error_aggregator)


async def digest_job() -> None:
    """Execute digest job with error monitoring."""
    error_aggregator = get_error_aggregator()
    logger.info("jobs.scheduler.digest_started")

    try:
        sent = await generate_and_send_digest()
        logger.info("jobs.scheduler.digest_completed", sent=sent)
    except Exception as e:
        logger.error(
            "jobs.scheduler.digest_failed",
            error=str(e),
            exc_info=True,
        )
        # Record error for aggregation
        error_aggregator.record_error(
            "digest_failed",
            {
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        # Check if we should send alert
        await _check_and_send_alert(error_aggregator)


async def openrouter_monitor_job() -> None:
    """Execute OpenRouter model monitoring job with error monitoring."""
    error_aggregator = get_error_aggregator()
    logger.info("jobs.scheduler.openrouter_monitor_started")

    try:
        await monitor_openrouter_main()
        logger.info("jobs.scheduler.openrouter_monitor_completed")
    except Exception as e:
        logger.error(
            "jobs.scheduler.openrouter_monitor_failed",
            error=str(e),
            exc_info=True,
        )
        # Record error for aggregation
        error_aggregator.record_error(
            "openrouter_monitor_failed",
            {
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        # Check if we should send alert
        await _check_and_send_alert(error_aggregator)


async def _check_and_send_alert(error_aggregator: ErrorAggregator) -> None:
    """Check error thresholds and send alert email if needed.

    Args:
        error_aggregator: The error aggregator instance.
    """
    if error_aggregator.should_send_alert():
        summary = error_aggregator.get_error_summary()

        # Build alert email
        subject = "🚨 AI Recruiter Alert: High Error Rate"
        text_body = f"""
High error rate detected in the AI Recruiter system.

Error Summary (last {summary["window_hours"]} hour):
"""
        for error_type, details in summary["errors"].items():
            text_body += (
                f"\n- {error_type}: {details['count']} errors (last seen: {details['last_seen']})"
            )

        text_body += f"""

Total errors: {summary["total_errors"]}

Action Required:
1. Check logs: journalctl -u air-scheduler -p err -n 50
2. Review health: curl http://localhost:8000/health | jq
3. Check monitoring endpoint: curl http://localhost:8000/monitoring/errors | jq

This is an automated alert from the AI Recruiter monitoring system.
"""

        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #dc3545;">🚨 AI Recruiter Alert: High Error Rate</h2>
    <p>High error rate detected in the AI Recruiter system.</p>

    <h3>Error Summary (last {summary["window_hours"]} hour):</h3>
    <ul>
"""
        for error_type, details in summary["errors"].items():
            html_body += f"""
        <li><strong>{error_type}</strong>: {details["count"]} errors<br>
            <small>Last seen: {details["last_seen"]}</small></li>
"""

        html_body += f"""
    </ul>

    <p><strong>Total errors:</strong> {summary["total_errors"]}</p>

    <h3>Action Required:</h3>
    <ol>
        <li>Check logs: <code>journalctl -u air-scheduler -p err -n 50</code></li>
        <li>Review health: <code>curl http://localhost:8000/health | jq</code></li>
        <li>Check monitoring endpoint: <code>curl http://localhost:8000/monitoring/errors | jq</code></li>
    </ol>

    <hr>
    <p style="color: #666; font-size: 12px;">
        This is an automated alert from the AI Recruiter monitoring system.
    </p>
</body>
</html>
"""

        # Send alert email
        try:
            sent = send_digest_email(subject, html_body, text_body)
            if sent:
                logger.info(
                    "jobs.scheduler.alert_sent",
                    total_errors=summary["total_errors"],
                    error_types=list(summary["errors"].keys()),
                )
                error_aggregator.mark_alert_sent()
            else:
                logger.warning(
                    "jobs.scheduler.alert_not_sent",
                    reason="email_service_unavailable",
                )
        except Exception as e:
            logger.error(
                "jobs.scheduler.alert_send_failed",
                error=str(e),
                exc_info=True,
            )


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the scheduler with all jobs."""
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)

    # Parse scrape hours (e.g., "5,17" -> [5, 17])
    scrape_hours = [int(h.strip()) for h in settings.scrape_hours.split(",")]

    # Add scrape jobs for each configured hour
    for hour in scrape_hours:
        scheduler.add_job(  # pyright: ignore[reportUnknownMemberType]
            scrape_job,
            CronTrigger(hour=hour, minute=0),
            id=f"scrape_{hour:02d}",
            name=f"Scrape at {hour:02d}:00",
            replace_existing=True,
        )
        logger.info(
            "jobs.scheduler.job_added",
            job_id=f"scrape_{hour:02d}",
            hour=hour,
            timezone=settings.scheduler_timezone,
        )

    # Parse digest hours (e.g., "6,18" -> [6, 18])
    digest_hours = [int(h.strip()) for h in settings.digest_hours.split(",")]

    # Add digest jobs for each configured hour (Mon-Fri only)
    for hour in digest_hours:
        scheduler.add_job(  # pyright: ignore[reportUnknownMemberType]
            digest_job,
            CronTrigger(hour=hour, minute=0, day_of_week="mon-fri"),
            id=f"digest_{hour:02d}",
            name=f"Digest at {hour:02d}:00 Mon-Fri",
            replace_existing=True,
        )
        logger.info(
            "jobs.scheduler.job_added",
            job_id=f"digest_{hour:02d}",
            hour=hour,
            days="mon-fri",
            timezone=settings.scheduler_timezone,
        )

    # Add OpenRouter model monitoring job (weekly on Monday at 9am)
    scheduler.add_job(  # pyright: ignore[reportUnknownMemberType]
        openrouter_monitor_job,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="openrouter_monitor",
        name="OpenRouter Model Monitor - Weekly Monday 09:00",
        replace_existing=True,
    )
    logger.info(
        "jobs.scheduler.job_added",
        job_id="openrouter_monitor",
        day="monday",
        hour=9,
        timezone=settings.scheduler_timezone,
    )

    return scheduler


async def main() -> None:
    """Main entry point for the scheduler."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info(
        "jobs.scheduler.starting",
        timezone=settings.scheduler_timezone,
        scrape_hours=settings.scrape_hours,
        digest_hours=settings.digest_hours,
    )

    scheduler = create_scheduler()
    scheduler.start()

    jobs = cast(list[Any], scheduler.get_jobs())  # pyright: ignore[reportUnknownMemberType]
    logger.info("jobs.scheduler.started", job_count=len(jobs))

    # Print scheduled jobs
    for job in jobs:
        logger.info(
            "jobs.scheduler.job_scheduled",
            job_id=str(job.id),
            job_name=str(job.name),
            next_run=str(job.next_run_time),
        )

    try:
        # Keep running
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("jobs.scheduler.stopping")
        scheduler.shutdown()
        logger.info("jobs.scheduler.stopped")


if __name__ == "__main__":
    asyncio.run(main())
