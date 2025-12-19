"""Health check endpoints for monitoring application and database status."""

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.monitoring import get_error_aggregator

logger = get_logger(__name__)

# Health check endpoints are typically at root (no prefix)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Enhanced health check with detailed system status.

    Checks:
    - Database connectivity and latency
    - Last successful scrape time (< 24 hours = healthy)
    - Email service configuration
    - Disk space (logs directory < 80% full)

    Returns 200 if healthy, 503 if unhealthy.

    Returns:
        dict: Health status with detailed checks.

    Raises:
        HTTPException: 503 if any critical check fails.

    Example response:
        {
            "status": "healthy",
            "timestamp": "2025-12-10T19:00:00Z",
            "checks": {
                "database": {"status": "ok", "latency_ms": 15},
                "last_scrape": {"status": "ok", "hours_ago": 6},
                "email": {"status": "ok", "configured": true},
                "disk": {"status": "ok", "percent_used": 45}
            }
        }
    """
    settings = get_settings()
    checks: dict[str, Any] = {}
    overall_status = "healthy"

    # Check 1: Database connectivity and latency
    try:
        db_start = datetime.now(UTC)
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=5.0)
        db_latency = (datetime.now(UTC) - db_start).total_seconds() * 1000
        checks["database"] = {
            "status": "ok",
            "latency_ms": round(db_latency, 1),
        }
    except TimeoutError:
        checks["database"] = {"status": "timeout", "latency_ms": None}
        overall_status = "unhealthy"
    except Exception as e:
        logger.error("health.database_check_failed", error=str(e), exc_info=True)
        checks["database"] = {"status": "error", "error": str(e)}
        overall_status = "unhealthy"

    # Check 2: Last successful scrape (< 24 hours = healthy)
    try:
        from app.demand.models import RoleScrapeRun

        result = await db.execute(
            select(RoleScrapeRun)
            .where(RoleScrapeRun.status == "completed")
            .order_by(desc(RoleScrapeRun.completed_at))
            .limit(1)
        )
        last_scrape = result.scalar_one_or_none()

        if last_scrape and last_scrape.completed_at:
            # Ensure completed_at is timezone-aware for comparison
            completed_at = last_scrape.completed_at
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=UTC)
            hours_ago = (datetime.now(UTC) - completed_at).total_seconds() / 3600
            if hours_ago < 24:
                checks["last_scrape"] = {
                    "status": "ok",
                    "hours_ago": round(hours_ago, 1),
                }
            else:
                checks["last_scrape"] = {
                    "status": "stale",
                    "hours_ago": round(hours_ago, 1),
                }
                overall_status = "degraded"
        else:
            checks["last_scrape"] = {"status": "no_data", "hours_ago": None}
            overall_status = "degraded"
    except Exception as e:
        logger.error("health.last_scrape_check_failed", error=str(e), exc_info=True)
        checks["last_scrape"] = {"status": "error", "error": str(e)}

    # Check 3: Email service configuration
    email_configured = bool(
        settings.mailgun_api_key and settings.mailgun_domain and settings.digest_recipient
    )
    checks["email"] = {
        "status": "ok" if email_configured else "not_configured",
        "configured": email_configured,
    }
    if not email_configured:
        overall_status = "degraded"  # Email alerts won't work, but not critical

    # Check 4: Disk space (logs directory)
    try:
        logs_path = Path("logs")
        if logs_path.exists():
            disk_stat = shutil.disk_usage(logs_path)
            percent_used = (disk_stat.used / disk_stat.total) * 100
            if percent_used < 80:
                checks["disk"] = {
                    "status": "ok",
                    "percent_used": round(percent_used, 1),
                }
            else:
                checks["disk"] = {
                    "status": "warning",
                    "percent_used": round(percent_used, 1),
                }
                overall_status = "degraded"
        else:
            checks["disk"] = {"status": "ok", "percent_used": 0}
    except Exception as e:
        logger.error("health.disk_check_failed", error=str(e), exc_info=True)
        checks["disk"] = {"status": "error", "error": str(e)}

    # Return 503 if unhealthy, 200 otherwise
    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": overall_status,
                "timestamp": datetime.now(UTC).isoformat(),
                "checks": checks,
            },
        )

    return {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }


@router.get("/health/db")
async def database_health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Database connectivity health check.

    Args:
        db: Database session dependency.

    Returns:
        dict: Health status of the database connection.

    Raises:
        HTTPException: 503 if database is not accessible.

    Example response:
        {"status": "healthy", "service": "database", "provider": "postgresql"}
    """
    try:
        # Execute a simple query to verify database connectivity
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "database",
            "provider": "postgresql",
        }
    except Exception as exc:
        logger.error("database.health_check_failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not accessible",
        ) from exc


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Readiness check for all application dependencies.

    Verifies that the application is ready to serve requests by checking
    all critical dependencies (database, configuration, etc.).

    Args:
        db: Database session dependency.

    Returns:
        dict: Readiness status with environment and dependency information.

    Raises:
        HTTPException: 503 if any dependency is not ready.

    Example response:
        {
            "status": "ready",
            "environment": "development",
            "database": "connected"
        }
    """
    settings = get_settings()

    try:
        # Verify database connectivity
        await db.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "environment": settings.environment,
            "database": "connected",
        }
    except Exception as exc:
        logger.error("health.readiness_check_failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application is not ready",
        ) from exc


@router.get("/monitoring/errors")
async def monitoring_errors() -> dict[str, Any]:
    """Get aggregated error statistics for monitoring.

    Returns error counts within the configured time window (1 hour)
    along with alert threshold information.

    This endpoint is for diagnostic purposes. For real-time monitoring,
    check application logs.

    Returns:
        dict: Error aggregation summary with counts and metadata.

    Example response:
        {
            "window_hours": 1,
            "errors": {
                "scrape_failed": {
                    "count": 2,
                    "last_seen": "2025-12-10T18:45:00Z"
                },
                "enrichment_timeout": {
                    "count": 15,
                    "last_seen": "2025-12-10T18:50:00Z"
                }
            },
            "total_errors": 17,
            "alert_threshold": 15,
            "should_alert": true
        }
    """
    error_aggregator = get_error_aggregator()
    summary = error_aggregator.get_error_summary()

    # Add alert threshold information (calibrated for batch jobs)
    summary["alert_threshold"] = 10  # Total error threshold
    summary["thresholds"] = {
        "scrape_failed": 1,
        "enrichment_errors": 8,
        "total_errors": 10,
    }
    summary["should_alert"] = error_aggregator.should_send_alert()

    return summary
