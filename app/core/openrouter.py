"""OpenRouter API client for fetching model information and usage stats.

This module provides functions to interact with OpenRouter's API to:
- Fetch all available models with pricing
- Get usage statistics for models
- Filter models by provider (Google, Anthropic, etc.)

Reference: https://openrouter.ai/docs#models
"""

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_all_models() -> list[dict[str, Any]]:
    """Fetch all models from OpenRouter API.

    Returns:
        List of model dictionaries with pricing and metadata.

    Raises:
        httpx.HTTPError: If API request fails.

    Example:
        models = await fetch_all_models()
        for model in models:
            print(f"{model['id']}: ${model['pricing']['prompt']}/1M tokens")
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://github.com/yourusername/air",  # Optional
                },
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            models: list[dict[str, Any]] = data.get("data", [])

            logger.info(
                "openrouter.models_fetched",
                count=len(models),
            )

            return models

        except httpx.HTTPError as e:
            logger.error(
                "openrouter.fetch_failed",
                exc_info=True,
                error=str(e),
            )
            raise


async def fetch_usage_stats() -> dict[str, Any]:
    """Fetch usage statistics from OpenRouter.

    Returns top models by usage across the platform.

    Returns:
        Dictionary with usage statistics.

    Raises:
        httpx.HTTPError: If API request fails.

    Note:
        This endpoint may require authentication or may not be publicly available.
        Check OpenRouter docs for availability.
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://openrouter.ai/api/v1/stats/usage",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                },
                timeout=30.0,
            )
            response.raise_for_status()

            data: dict[str, Any] = response.json()

            logger.info("openrouter.usage_stats_fetched")

            return data

        except httpx.HTTPError as e:
            # Non-critical - usage stats are optional
            logger.warning(
                "openrouter.usage_stats_failed",
                error=str(e),
            )
            return {}


def filter_models_by_provider(
    models: list[dict[str, Any]], providers: list[str]
) -> list[dict[str, Any]]:
    """Filter models by provider.

    Args:
        models: List of model dictionaries from OpenRouter API.
        providers: List of provider prefixes (e.g., ["google", "anthropic"]).

    Returns:
        Filtered list of models matching the providers.

    Example:
        all_models = await fetch_all_models()
        google_models = filter_models_by_provider(all_models, ["google"])
    """
    filtered = []

    for model in models:
        model_id = model.get("id", "")
        for provider in providers:
            if model_id.startswith(f"{provider}/"):
                filtered.append(model)
                break

    logger.info(
        "openrouter.models_filtered",
        total=len(models),
        filtered=len(filtered),
        providers=providers,
    )

    return filtered


def parse_model_data(api_model: dict[str, Any]) -> dict[str, Any]:
    """Parse OpenRouter API model data into our schema format.

    Args:
        api_model: Raw model dict from OpenRouter API.

    Returns:
        Dictionary with fields matching OpenRouterModel schema.

    Example:
        api_model = {"id": "google/gemini-2.5-flash-lite", "pricing": {...}, ...}
        parsed = parse_model_data(api_model)
        # parsed = {"model_id": "google/gemini-2.5-flash-lite", "input_price": 0.10, ...}
    """
    model_id = api_model["id"]
    provider = model_id.split("/")[0] if "/" in model_id else "unknown"

    # Extract pricing (convert from per-token to per-1M tokens)
    pricing = api_model.get("pricing", {})
    input_price = float(pricing.get("prompt", 0)) * 1_000_000
    output_price = float(pricing.get("completion", 0)) * 1_000_000

    # Determine performance tier from model name
    model_name = api_model.get("name", model_id)
    performance_tier = "unknown"
    if "lite" in model_name.lower() or "flash" in model_name.lower():
        performance_tier = "flash"
    elif "pro" in model_name.lower():
        performance_tier = "pro"
    elif "opus" in model_name.lower():
        performance_tier = "opus"

    return {
        "model_id": model_id,
        "model_name": model_name,
        "input_price": input_price,
        "output_price": output_price,
        "context_window": api_model.get("context_length", 128000),
        "supports_tools": True,  # Assume true, can be updated manually
        "supports_vision": "vision" in model_name.lower(),
        "provider": provider,
        "performance_tier": performance_tier,
        "active": True,
        "metadata_": {
            "top_provider": api_model.get("top_provider"),
            "architecture": api_model.get("architecture"),
        },
    }
