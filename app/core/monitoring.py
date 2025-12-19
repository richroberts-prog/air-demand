"""Error aggregation and monitoring for production alerting.

This module provides in-memory error tracking with:
- Sliding time window (last N hours)
- Error type aggregation
- Threshold-based alerting
- Thread-safe concurrent access
"""

import threading
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any


class ErrorAggregator:
    """Thread-safe error aggregation with sliding time window.

    Tracks errors by type and determines when alert thresholds are crossed.
    Errors older than the window duration are automatically excluded.

    Example:
        >>> aggregator = ErrorAggregator(window_hours=1)
        >>> aggregator.record_error("scrape_failed", {"role_id": 123})
        >>> if aggregator.should_send_alert():
        ...     send_email_alert(aggregator.get_error_summary())
    """

    def __init__(self, window_hours: int = 1) -> None:
        """Initialize error aggregator.

        Args:
            window_hours: How many hours of errors to track (default: 1).
        """
        self.window_hours = window_hours
        self.window_duration = timedelta(hours=window_hours)
        self._errors: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._alert_sent_at: datetime | None = None
        self._alert_cooldown = timedelta(hours=1)  # Don't spam alerts

    def record_error(self, error_type: str, context: dict[str, Any]) -> None:
        """Record an error occurrence.

        Args:
            error_type: Type of error (e.g., "scrape_failed", "enrichment_timeout").
            context: Additional context about the error.
        """
        with self._lock:
            self._errors[error_type].append(
                {
                    "timestamp": datetime.now(UTC),
                    "context": context,
                }
            )
            # Clean old errors
            self._clean_old_errors()

    def get_error_summary(self) -> dict[str, Any]:
        """Get aggregated error counts within the time window.

        Returns:
            Dictionary with error counts and metadata.
        """
        with self._lock:
            self._clean_old_errors()

            summary: dict[str, Any] = {
                "window_hours": self.window_hours,
                "errors": {},
                "total_errors": 0,
            }

            for error_type, errors in self._errors.items():
                if errors:
                    summary["errors"][error_type] = {
                        "count": len(errors),
                        "last_seen": errors[-1]["timestamp"].isoformat(),
                    }
                    summary["total_errors"] += len(errors)

            return summary

    def should_send_alert(self) -> bool:
        """Determine if alert threshold is crossed.

        Alert thresholds (calibrated for batch jobs running 2x daily):
        - 1+ scraper failures in window (any failure is critical)
        - 8+ enrichment errors in window (>50% failing in single scrape)
        - Overall 10+ errors in window (multiple failures in single run)

        Also enforces cooldown period to prevent alert fatigue.

        Returns:
            True if alert should be sent.
        """
        with self._lock:
            self._clean_old_errors()

            # Check cooldown period
            if self._alert_sent_at:
                time_since_alert = datetime.now(UTC) - self._alert_sent_at
                if time_since_alert < self._alert_cooldown:
                    return False

            # Count errors by type
            scrape_failures = len(self._errors.get("scrape_failed", []))
            digest_failures = len(self._errors.get("digest_failed", []))
            enrichment_errors = sum(
                len(self._errors.get(key, []))
                for key in ["enrichment_timeout", "enrichment_api_error", "enrichment_parse_error"]
            )
            total_errors = sum(len(errors) for errors in self._errors.values())

            # Check thresholds (calibrated for batch jobs)
            if scrape_failures >= 1:
                return True
            if digest_failures >= 1:
                return True
            if enrichment_errors >= 8:
                return True
            if total_errors >= 10:
                return True

            return False

    def mark_alert_sent(self) -> None:
        """Mark that an alert was sent to enforce cooldown."""
        with self._lock:
            self._alert_sent_at = datetime.now(UTC)

    def _clean_old_errors(self) -> None:
        """Remove errors outside the time window (called with lock held)."""
        cutoff = datetime.now(UTC) - self.window_duration

        for error_type in list(self._errors.keys()):
            self._errors[error_type] = [
                error for error in self._errors[error_type] if error["timestamp"] > cutoff
            ]
            # Remove error type if no errors remain
            if not self._errors[error_type]:
                del self._errors[error_type]


# Global error aggregator instance
_error_aggregator: ErrorAggregator | None = None
_aggregator_lock = threading.Lock()


def get_error_aggregator() -> ErrorAggregator:
    """Get the global error aggregator instance (singleton).

    Returns:
        The error aggregator instance.
    """
    global _error_aggregator

    if _error_aggregator is None:
        with _aggregator_lock:
            if _error_aggregator is None:
                _error_aggregator = ErrorAggregator(window_hours=1)

    return _error_aggregator
