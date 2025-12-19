"""Data extraction from Paraform tRPC responses - v0.1 simplified.

For v0.1, we just extract the roles array from the tRPC response.
All data is saved as raw JSONB, no transformation needed.
"""

from typing import Any, cast

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_roles_from_browse(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract roles array from tRPC browse response.

    tRPC nests data as: {"result": {"data": {"json": [...roles array...]}}}

    Args:
        response: Full tRPC response from browse_roles().

    Returns:
        List of role objects, or empty list if parsing fails.
    """
    try:
        roles = response["result"]["data"]["json"]
        if not isinstance(roles, list):
            logger.error(
                "jobs.scraper.extractor.browse_parse_unexpected_type",
                expected="list",
                got=type(roles).__name__,
            )
            return []
        # Type narrowing: we know roles is a list now
        roles_list = cast(list[dict[str, Any]], roles)
        logger.info("jobs.scraper.extractor.browse_parsed", roles_count=len(roles_list))
        return roles_list
    except (KeyError, TypeError) as e:
        logger.error(
            "jobs.scraper.extractor.browse_parse_failed",
            error=str(e),
            error_type=type(e).__name__,
            response_keys=list(response.keys()),
            exc_info=True,
        )
        return []
