"""FastAPI dependencies for core services."""

from typing import Annotated

from fastapi import Depends
from pydantic_ai import Agent

from app.core.llm import get_llm_client


async def get_llm_agent() -> Agent[None, None]:
    """FastAPI dependency to inject LLM agent.

    Usage in routes:
        ```python
        @router.post("/score")
        async def score_role(
            role_data: RoleSchema,
            agent: Annotated[Agent, Depends(get_llm_agent)]
        ):
            result = await agent.run(...)
            return result
        ```

    Returns:
        Cached LLM Agent instance (singleton).
    """
    return get_llm_client()


# Type alias for cleaner route signatures
LLMAgentDep = Annotated[Agent[None, None], Depends(get_llm_agent)]
