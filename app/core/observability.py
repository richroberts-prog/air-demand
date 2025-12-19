"""Langfuse observability integration for supply agents.

This module provides:
- Singleton Langfuse client with graceful degradation
- Auto-instrumentation for Pydantic AI agents
- trace_pipeline() context manager for metadata enrichment
"""

import atexit
import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Global Langfuse client instance
_langfuse_client: Any | None = None


def init() -> None:
    """Initialize Langfuse with auto-instrumentation and graceful degradation.

    Configures:
    - Auto-instrumentation for Pydantic AI agents
    - Environment variables for Langfuse client
    - Flush on shutdown via atexit hook

    Gracefully handles:
    - Missing Langfuse credentials (logs warning, continues)
    - Langfuse server unavailable (logs warning, continues)

    This function should be called once during application startup.
    """
    global _langfuse_client

    settings = get_settings()

    # Check if Langfuse credentials are configured
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning(
            "observability.disabled",
            reason="Langfuse credentials not configured (langfuse_public_key or langfuse_secret_key missing)",
        )
        _langfuse_client = None
        return

    try:
        # Set environment variables for Langfuse client
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
        os.environ["LANGFUSE_HOST"] = settings.langfuse_host

        # Import Langfuse dynamically to avoid hard dependency
        from langfuse import Langfuse

        # Create Langfuse client
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

        # Enable auto-instrumentation for Pydantic AI agents
        Agent.instrument_all()

        # Register flush on shutdown
        atexit.register(_langfuse_client.flush)

        logger.info(
            "observability.initialized",
            host=settings.langfuse_host,
            auto_instrumentation=True,
        )

    except Exception as e:
        logger.warning(
            "observability.initialization_failed",
            error=str(e),
            reason="Langfuse unavailable - continuing without observability",
            exc_info=True,
        )
        _langfuse_client = None


@lru_cache(maxsize=1)
def get_client() -> Any | None:  # noqa: ANN401
    """Get singleton Langfuse client instance.

    Returns:
        Langfuse client if initialized, None if disabled or unavailable.
    """
    return _langfuse_client


@contextmanager
def trace_pipeline(
    user_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[None]:
    """Context manager for enriching agent traces with metadata.

    Adds user_id, tags, and custom metadata to the current Pydantic AI agent trace.
    This provides rich observability for debugging, cost tracking, and performance analysis.

    Args:
        user_id: Candidate/user ID for trace attribution (optional).
        tags: List of tags for filtering (e.g., ["identity-extraction", "gate-01"]).
        metadata: Custom metadata dict (e.g., {"linkedin_member_id": "123", "has_profile_photo": True}).

    Yields:
        None: Control returns to caller with trace context active.

    Example:
        ```python
        from app.core import observability

        async def extract_identity_features(
            linkedin_data: dict[str, Any],
            candidate_id: str,
        ) -> IdentityFeatures:
            agent = _get_agent()

            with observability.trace_pipeline(
                user_id=str(candidate_id),
                tags=["identity-extraction", "gate-01"],
                metadata={
                    "linkedin_member_id": linkedin_data.get("member_id"),
                    "has_profile_photo": bool(linkedin_data.get("profile_photo_url")),
                },
            ):
                result = await asyncio.wait_for(
                    agent.run(prompt),
                    timeout=settings.llm_timeout,
                )

            return result.data
        ```

    Notes:
        - If Langfuse client is None (disabled/unavailable), this is a no-op
        - Exceptions during trace enrichment are logged and suppressed (graceful degradation)
        - This context manager is re-entrant and can be nested
    """
    if _langfuse_client is None:
        # Observability disabled - no-op context manager
        yield
        return

    try:
        # Import propagate_attributes dynamically
        from langfuse import propagate_attributes

        # Build attributes dict
        attributes: dict[str, Any] = {}

        if user_id is not None:
            attributes["user_id"] = user_id

        if tags is not None and len(tags) > 0:
            attributes["tags"] = tags

        if metadata is not None and len(metadata) > 0:
            attributes["metadata"] = metadata

        # Use propagate_attributes to enrich current trace
        with propagate_attributes(**attributes):
            yield

    except Exception as e:
        logger.warning(
            "observability.trace_enrichment_failed",
            error=str(e),
            reason="Failed to enrich trace with metadata - continuing without enrichment",
            exc_info=True,
        )
        # Gracefully degrade - yield without enrichment
        yield
