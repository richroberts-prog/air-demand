"""Playwright authentication and session management for Paraform scraper.

This module handles:
- Browser session persistence via storage_state (cookies/localStorage)
- Session validation and expiry detection
- Manual login flow for first-time authentication
- In-memory session caching for performance
"""

import base64
import json
import os
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Playwright, async_playwright

from app.core.logging import get_logger

logger = get_logger(__name__)

# Session storage path (gitignored)
SESSION_PATH = Path("paraform_session.json")

# In-memory cache for current session
_session_cache: BrowserContext | None = None
_playwright_instance: Playwright | None = None


def ensure_session_file() -> None:
    """Create session file from env var if it doesn't exist.

    On Render, PARAFORM_SESSION_JSON environment variable contains
    the base64-encoded session file. This function decodes and writes
    it to disk if the local file doesn't exist.
    """
    if SESSION_PATH.exists():
        return

    session_b64 = os.getenv("PARAFORM_SESSION_JSON")
    if not session_b64:
        logger.warning(
            "jobs.scraper.auth.no_session",
            message="No session file and no PARAFORM_SESSION_JSON env var",
        )
        return

    try:
        session_json = base64.b64decode(session_b64).decode("utf-8")
        SESSION_PATH.write_text(session_json)
        logger.info("jobs.scraper.auth.session_restored_from_env", path=str(SESSION_PATH))
    except Exception as e:
        logger.error("jobs.scraper.auth.session_restore_failed", error=str(e), exc_info=True)


async def save_session(context: BrowserContext) -> None:
    """Save browser session state to file.

    Persists cookies, localStorage, and other authentication state
    to enable session reuse across scraper runs.

    Args:
        context: Authenticated Playwright browser context.

    Raises:
        OSError: If session file cannot be written.
    """
    logger.info("jobs.scraper.auth.session_save_started", path=str(SESSION_PATH))
    try:
        await context.storage_state(path=str(SESSION_PATH))
        logger.info("jobs.scraper.auth.session_save_completed", path=str(SESSION_PATH))
    except Exception as e:
        logger.error(
            "jobs.scraper.auth.session_save_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


async def load_session() -> dict[str, Any] | None:
    """Load session state from file.

    Returns:
        Session state dictionary if file exists, None otherwise.
    """
    if not SESSION_PATH.exists():
        logger.info("jobs.scraper.auth.session_not_found", path=str(SESSION_PATH))
        return None

    logger.info("jobs.scraper.auth.session_load_started", path=str(SESSION_PATH))
    try:
        with SESSION_PATH.open() as f:
            state: dict[str, Any] = json.load(f)
        logger.info("jobs.scraper.auth.session_load_completed", path=str(SESSION_PATH))
        return state
    except Exception as e:
        logger.error(
            "jobs.scraper.auth.session_load_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return None


async def is_session_valid(context: BrowserContext) -> bool:
    """Test if session is still valid.

    Attempts to access dashboard page - if redirected to login, session expired.

    Args:
        context: Browser context to validate.

    Returns:
        True if session is valid, False if expired.
    """
    logger.info("jobs.scraper.auth.session_validation_started")
    page = await context.new_page()
    try:
        response = await page.goto("https://www.paraform.com/dashboard", timeout=30000)
        if response is None:
            logger.warning("jobs.scraper.auth.session_validation_no_response")
            return False

        is_valid = "login" not in response.url
        logger.info(
            "jobs.scraper.auth.session_validation_completed",
            is_valid=is_valid,
            final_url=response.url,
        )
        return is_valid
    except Exception as e:
        logger.error(
            "jobs.scraper.auth.session_validation_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return False
    finally:
        await page.close()


async def manual_login() -> BrowserContext:
    """Interactive manual login flow.

    Opens a visible browser window for the user to complete magic link authentication.
    Waits for user confirmation before saving session and returning.

    Returns:
        Authenticated browser context with saved session.

    Raises:
        RuntimeError: If Playwright initialization fails.
    """
    global _playwright_instance, _session_cache

    logger.info("jobs.scraper.auth.manual_login_started")

    try:
        _playwright_instance = await async_playwright().start()
        browser = await _playwright_instance.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.paraform.com/login")
        logger.info("jobs.scraper.auth.manual_login_browser_opened")

        print("\n" + "=" * 60)
        print("Paraform Manual Login")
        print("=" * 60)
        print("1. Complete the login flow in the browser window")
        print("2. Wait for the magic link email and click it")
        print("3. Verify you see the Paraform dashboard")
        print("4. Press ENTER here to save the session")
        print("=" * 60 + "\n")

        input("Press ENTER when logged in...")

        # Verify we're actually logged in
        current_url = page.url
        if "dashboard" not in current_url and "browse" not in current_url:
            logger.warning(
                "jobs.scraper.auth.manual_login_incomplete",
                current_url=current_url,
            )
            print("Warning: You may not be logged in. Current URL:", current_url)
            confirm = input("Continue anyway? (y/N): ")
            if confirm.lower() != "y":
                await browser.close()
                raise RuntimeError("Login not completed")

        await save_session(context)
        _session_cache = context

        logger.info("jobs.scraper.auth.manual_login_completed")
        print("Session saved successfully!\n")

        return context

    except Exception as e:
        logger.error(
            "jobs.scraper.auth.manual_login_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


async def get_session() -> BrowserContext:
    """Get authenticated browser context.

    Returns cached session if available, otherwise loads from storage file.
    Does NOT validate session - caller should handle expired sessions.

    Returns:
        BrowserContext with Paraform session.

    Raises:
        ValueError: If no session file exists (manual_login required).
        RuntimeError: If Playwright initialization fails.
    """
    global _session_cache, _playwright_instance

    # Ensure session file exists (restore from env var if needed)
    ensure_session_file()

    # Return cached session if available
    if _session_cache is not None:
        logger.info("jobs.scraper.auth.session_cache_hit")
        return _session_cache

    # Load session from file
    session_state = await load_session()
    if session_state is None:
        logger.error("jobs.scraper.auth.session_missing")
        raise ValueError(
            "No session found. Run manual_login() first:\n"
            "  python -c 'import asyncio; from app.demand.scraper.auth import manual_login; "
            "asyncio.run(manual_login())'"
        )

    logger.info("jobs.scraper.auth.session_restore_started")

    try:
        # Initialize Playwright if not already done
        if _playwright_instance is None:
            _playwright_instance = await async_playwright().start()

        browser = await _playwright_instance.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=session_state)  # type: ignore[arg-type]

        _session_cache = context
        logger.info("jobs.scraper.auth.session_restore_completed")

        return context

    except Exception as e:
        logger.error(
            "jobs.scraper.auth.session_restore_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise RuntimeError(f"Failed to restore session: {e}") from e


async def cleanup_session() -> None:
    """Clean up Playwright resources.

    Should be called on application shutdown to properly close browsers.
    """
    global _session_cache, _playwright_instance

    logger.info("jobs.scraper.auth.cleanup_started")

    if _session_cache is not None:
        try:
            await _session_cache.close()
            _session_cache = None
            logger.info("jobs.scraper.auth.context_closed")
        except Exception as e:
            logger.warning(
                "jobs.scraper.auth.context_close_failed",
                error=str(e),
            )

    if _playwright_instance is not None:
        try:
            await _playwright_instance.stop()
            _playwright_instance = None
            logger.info("jobs.scraper.auth.playwright_stopped")
        except Exception as e:
            logger.warning(
                "jobs.scraper.auth.playwright_stop_failed",
                error=str(e),
            )

    logger.info("jobs.scraper.auth.cleanup_completed")
