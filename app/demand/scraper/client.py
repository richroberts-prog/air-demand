"""tRPC API client for Paraform endpoints.

Handles:
- tRPC request formatting with URL-encoded JSON parameters
- searchActiveRoles endpoint for role listings
- Rate limiting (2s delay between requests)
- Error handling for network/API failures
"""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from playwright.async_api import BrowserContext

from app.core.logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def rate_limit(delay_seconds: float = 2.0) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Rate limit decorator - adds delay after function execution.

    Prevents API bans by spacing out requests. Legacy saw 20% failures without this.

    Args:
        delay_seconds: Seconds to wait after function completes.

    Returns:
        Decorated async function with rate limiting.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = await func(*args, **kwargs)  # type: ignore[misc]
            await asyncio.sleep(delay_seconds)
            return cast(T, result)

        return cast(Callable[P, T], wrapper)

    return decorator


@rate_limit(delay_seconds=2.0)
async def browse_roles(
    context: BrowserContext, filters: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Fetch role listings from Paraform searchActiveRoles API.

    Uses Playwright page.evaluate to make GET request with URL-encoded JSON params.
    The actual endpoint is `/api/trpc/activeRoles.searchActiveRoles`.
    Applies 2s rate limiting after completion.

    Args:
        context: Authenticated Playwright browser context.
        filters: Optional filters for role search.

    Returns:
        tRPC response with roles array at result.data.json (direct array, not nested).

    Raises:
        RuntimeError: If API request fails or returns non-JSON response.
    """
    logger.info("jobs.scraper.client.browse_started", filters=filters)

    page = await context.new_page()
    try:
        # Navigate to Paraform browse page first (establishes context)
        await page.goto("https://www.paraform.com/browse", wait_until="domcontentloaded")

        # Build search parameters (default: all roles, no filters)
        search_params: dict[str, Any] = {
            "client": False,
            "statuses": [],
            "smart_filters": [],
            "location": [],
            "workplace": [],
            "role_type": [],
            "industry": [],
            "tech_stack": [],
            "size": [],
            "yoe_experience": {"min": None, "max": None},
            "salary": {"min": None, "max": None},
            "investors": [],
            "visa": [],
            "talent_density": [],
            "show_favourites": False,
            "show_agency_roles": False,
            "role_statuses": [],
            "ideal_company_ids": [],
            "hiring_count": {"min": None, "max": None},
            "rating": {"min": None, "max": None},
            "last_active": {"min": None, "max": None},
            "ai_role_titles": [],
            "currently_interviewing": False,
            "last_funding_round": [],
            "posted_at": {"min": None, "max": None},
            "responsiveness": {"min": None, "max": None},
            "active_interviews": {"min": None, "max": None},
            "account_manager": [],
            "recruiter": [],
            "not_applied": False,
            "matchProfilePreferences": False,
            "query": "",
        }

        # Merge with provided filters
        if filters:
            search_params.update(filters)

        # Build tRPC input format: {json: {...params...}}
        trpc_input: dict[str, Any] = {"json": search_params}

        # Execute fetch in browser context (includes auth cookies)
        response_data: dict[str, Any] = await page.evaluate(
            """
            async (input) => {
                // Encode the input for URL
                const encoded = encodeURIComponent(JSON.stringify(input));
                const url = `/api/trpc/activeRoles.searchActiveRoles?input=${encoded}`;

                const res = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }

                return await res.json();
            }
        """,
            trpc_input,
        )

        # Extract role count for logging
        roles_count = 0
        try:
            # Response structure: {result: {data: {json: [...roles array...]}}}
            roles: Any = response_data.get("result", {}).get("data", {}).get("json", [])
            if isinstance(roles, list):
                roles_count = len(cast(list[Any], roles))  # type: ignore[redundant-cast]
        except (KeyError, TypeError):
            pass

        logger.info("jobs.scraper.client.browse_completed", roles_count=roles_count)

        return response_data

    except Exception as e:
        logger.error(
            "jobs.scraper.client.browse_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Re-raise with context
        raise RuntimeError(f"Failed to fetch roles from browse API: {e}") from e

    finally:
        await page.close()


@rate_limit(delay_seconds=2.0)
async def get_role_detail(context: BrowserContext, role_id: str) -> dict[str, Any]:
    """Fetch detailed role information from Paraform getRoleByIdDetailed API.

    The browse API only returns basic role info with company one-liner.
    This endpoint fetches the full role description, detailed requirements,
    application questions, and complete company description.

    Args:
        context: Authenticated Playwright browser context.
        role_id: Paraform role ID to fetch.

    Returns:
        tRPC response with detailed role data including:
        - description (HTML): Full role description with "What You'll Do"
        - requirements (array): Detailed requirements with type/group classification
        - experience_info (str): Additional experience requirements
        - role_question (array): Application questions
        - company.description (HTML): Full company description

    Raises:
        RuntimeError: If API request fails or returns non-JSON response.
    """
    logger.info("jobs.scraper.client.detail_started", role_id=role_id)

    page = await context.new_page()
    try:
        # Navigate to browse page first (establishes context)
        await page.goto("https://www.paraform.com/browse", wait_until="domcontentloaded")

        # Build tRPC input format: {json: {role_id: "..."}}
        trpc_input = {"json": {"role_id": role_id}}

        # Execute fetch in browser context (includes auth cookies)
        response_data: dict[str, Any] = await page.evaluate(
            """
            async (input) => {
                // Encode the input for URL
                const encoded = encodeURIComponent(JSON.stringify(input));
                const url = `/api/trpc/role.getRoleByIdDetailed?input=${encoded}`;

                const res = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }

                return await res.json();
            }
        """,
            trpc_input,
        )

        # Verify we got detail data
        detail_data = response_data.get("result", {}).get("data", {}).get("json", {})
        has_description = "description" in detail_data

        logger.info(
            "jobs.scraper.client.detail_completed",
            role_id=role_id,
            has_description=has_description,
            has_requirements="requirements" in detail_data,
        )

        return response_data

    except Exception as e:
        logger.error(
            "jobs.scraper.client.detail_failed",
            role_id=role_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Re-raise with context
        raise RuntimeError(f"Failed to fetch role detail for {role_id}: {e}") from e

    finally:
        await page.close()


@rate_limit(delay_seconds=2.0)
async def get_role_detail_simple(context: BrowserContext, role_id: str) -> dict[str, Any]:
    """Fetch role data from getRoleByIdSimple API.

    This endpoint returns additional fields not in the browse API:
    - companyTip: Manager intro HTML with investor mentions
    - selling_points: Pitch bullets HTML with company highlights
    - equity: Equity compensation description
    - requirements: Detailed requirements with priority/type

    These HTML fields contain valuable intel (investors, advisors, growth signals)
    that can be extracted via LLM for enhanced scoring.

    Args:
        context: Authenticated Playwright browser context.
        role_id: Paraform role ID to fetch.

    Returns:
        tRPC response with extended role data.

    Raises:
        RuntimeError: If API request fails.
    """
    logger.info("jobs.scraper.client.detail_simple_started", role_id=role_id)

    page = await context.new_page()
    try:
        # Navigate to browse page first (establishes context)
        await page.goto("https://www.paraform.com/browse", wait_until="domcontentloaded")

        # Build tRPC input format: {json: {role_id: "..."}}
        trpc_input = {"json": {"role_id": role_id}}

        # Execute fetch in browser context (includes auth cookies)
        response_data: dict[str, Any] = await page.evaluate(
            """
            async (input) => {
                // Encode the input for URL
                const encoded = encodeURIComponent(JSON.stringify(input));
                const url = `/api/trpc/role.getRoleByIdSimple?input=${encoded}`;

                const res = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }

                return await res.json();
            }
        """,
            trpc_input,
        )

        # Verify we got the key fields
        detail_data = response_data.get("result", {}).get("data", {}).get("json", {})
        has_company_tip = "companyTip" in detail_data
        has_selling_points = "selling_points" in detail_data

        logger.info(
            "jobs.scraper.client.detail_simple_completed",
            role_id=role_id,
            has_company_tip=has_company_tip,
            has_selling_points=has_selling_points,
        )

        return response_data

    except Exception as e:
        logger.error(
            "jobs.scraper.client.detail_simple_failed",
            role_id=role_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Re-raise with context
        raise RuntimeError(f"Failed to fetch role detail (simple) for {role_id}: {e}") from e

    finally:
        await page.close()


@rate_limit(delay_seconds=2.0)
async def get_intake_calls(context: BrowserContext, role_id: str) -> dict[str, Any]:
    """Fetch intake call meetings for a role.

    Args:
        context: Authenticated Playwright browser context.
        role_id: Paraform role ID to fetch intake calls for.

    Returns:
        tRPC response with list of intake call meetings.

    Raises:
        RuntimeError: If API request fails.
    """
    logger.info("jobs.scraper.client.intake_calls_started", role_id=role_id)

    page = await context.new_page()
    try:
        await page.goto("https://www.paraform.com/browse", wait_until="domcontentloaded")

        trpc_input = {"json": {"role_id": role_id}}

        response_data: dict[str, Any] = await page.evaluate(
            """
            async (input) => {
                const encoded = encodeURIComponent(JSON.stringify(input));
                const url = `/api/trpc/meetings.getAllIntakeAndOnboardingCallsByRoleId?input=${encoded}`;

                const res = await fetch(url, {
                    method: 'GET',
                    headers: {'Content-Type': 'application/json'},
                });

                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }

                return await res.json();
            }
        """,
            trpc_input,
        )

        meetings: Any = response_data.get("result", {}).get("data", {}).get("json", [])
        meetings_count = len(cast(list[Any], meetings)) if isinstance(meetings, list) else 0  # type: ignore[redundant-cast]
        logger.info(
            "jobs.scraper.client.intake_calls_completed",
            role_id=role_id,
            meetings_count=meetings_count,
        )

        return response_data

    except Exception as e:
        logger.error(
            "jobs.scraper.client.intake_calls_failed",
            role_id=role_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise RuntimeError(f"Failed to fetch intake calls for {role_id}: {e}") from e

    finally:
        await page.close()


# Alias for briefing service (matches plan naming)
get_role_meetings = get_intake_calls


@rate_limit(delay_seconds=2.0)
async def get_meeting_transcript(context: BrowserContext, meeting_id: str) -> dict[str, Any]:
    """Fetch meeting transcript by meeting ID.

    Args:
        context: Authenticated Playwright browser context.
        meeting_id: Meeting ID to fetch transcript for.

    Returns:
        tRPC response with meeting details including transcript.

    Raises:
        RuntimeError: If API request fails.
    """
    logger.info("jobs.scraper.client.meeting_transcript_started", meeting_id=meeting_id)

    page = await context.new_page()
    try:
        await page.goto("https://www.paraform.com/browse", wait_until="domcontentloaded")

        trpc_input = {"json": {"meeting_id": meeting_id}}

        response_data: dict[str, Any] = await page.evaluate(
            """
            async (input) => {
                const encoded = encodeURIComponent(JSON.stringify(input));
                const url = `/api/trpc/meetings.getMeetingById?input=${encoded}`;

                const res = await fetch(url, {
                    method: 'GET',
                    headers: {'Content-Type': 'application/json'},
                });

                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }

                return await res.json();
            }
        """,
            trpc_input,
        )

        meeting_data = response_data.get("result", {}).get("data", {}).get("json", {})
        has_transcript = "transcription" in meeting_data

        logger.info(
            "jobs.scraper.client.meeting_transcript_completed",
            meeting_id=meeting_id,
            has_transcript=has_transcript,
        )

        return response_data

    except Exception as e:
        logger.error(
            "jobs.scraper.client.meeting_transcript_failed",
            meeting_id=meeting_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise RuntimeError(f"Failed to fetch meeting transcript {meeting_id}: {e}") from e

    finally:
        await page.close()
