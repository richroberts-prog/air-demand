"""LLM client setup with OpenRouter and Pydantic AI.

This module provides a singleton LLM client for structured AI interactions.
Uses OpenRouter as provider with Gemini 2.5 Flash Lite as default model.
"""

import os
from functools import lru_cache

from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm_client() -> Agent[None, None]:
    """Get cached LLM agent instance.

    Creates a Pydantic AI Agent configured with OpenRouter model.
    This agent is a singleton (cached) for the application lifetime.

    Returns:
        Configured Pydantic AI Agent with OpenRouter model.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set in environment.
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        logger.error("core.llm.config_missing", error="OPENROUTER_API_KEY not set")
        raise ValueError(
            "OPENROUTER_API_KEY environment variable must be set. "
            "Get your key from https://openrouter.ai/keys"
        )

    # Set API key in environment for OpenRouter
    os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

    model = OpenRouterModel(settings.llm_model)

    agent = Agent(
        model,
        system_prompt=(
            "You are a specialized AI assistant for analyzing job roles. "
            "Classify roles precisely using provided categories and return structured JSON outputs."
        ),
    )

    logger.info(
        "core.llm.initialized",
        model=settings.llm_model,
        provider="openrouter",
        temperature=settings.llm_temperature,
    )

    return agent  # type: ignore[return-value]
