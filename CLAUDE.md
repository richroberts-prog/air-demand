# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI + PostgreSQL application using **vertical slice architecture**, optimized for AI-assisted development. Python 3.12+, strict type checking with MyPy and Pyright.

## Core Principles

**KISS** (Keep It Simple, Stupid)

- Prefer simple, readable solutions over clever abstractions

**YAGNI** (You Aren't Gonna Need It)

- Don't build features until they're actually needed

**Vertical Slice Architecture**

- Each feature owns its database models, schemas, routes, and business logic
- Features live in separate directories directly under `app/` (e.g., `app/products/`, `app/orders/`)
- Shared utilities go in `app/shared/` only when used by 3+ features
- Core infrastructure (`app/core/`) is shared across all features

**Type Safety (CRITICAL)**

- Strict type checking enforced (MyPy + Pyright in strict mode)
- All functions, methods, and variables MUST have type annotations
- Zero type suppressions allowed without documented justification
- No `Any` types without explicit justification
- Test files have relaxed typing rules (see pyproject.toml)
- See `docs/standards/mypy-standard.md` and `docs/standards/pyright-standard.md` for details

**AI-Optimized Patterns**

- Structured logging: Use `domain.component.action_state` pattern
  - Format: `{domain}.{component}.{action}_{state}`
  - Examples: `user.registration_started`, `product.create_completed`, `database.health_check_failed`
  - See `docs/standards/logging-standard.md` for complete event taxonomy
- Request correlation: All logs include `request_id` automatically via context vars
- Consistent naming: Predictable patterns for AI code generation

## Essential Commands

### Development

```bash
# Start development server (port 8123)
uv run uvicorn app.main:app --reload --port 8123
```

### Testing

```bash
# Run all tests (~40 tests, <1s execution)
uv run pytest -v

# Run integration tests only
uv run pytest -v -m integration

# Run specific test
uv run pytest -v app/core/tests/test_database.py::test_function_name
```

### Type Checking

```bash
# MyPy (strict mode) - must be green
uv run mypy app/

# Pyright (strict mode) - must be green
uv run pyright app/
```

### Linting & Formatting

```bash
# Check linting - must be green
uv run ruff check .

# Auto-format code
uv run ruff format .
```

### Database Migrations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Start PostgreSQL (Docker)
docker-compose up -d
```

### Docker

```bash
# Build and start all services
docker-compose up -d --build

# View app logs
docker-compose logs -f app

# Stop all services
docker-compose down
```

## Architecture

### Directory Structure

```
app/
├── core/           # Infrastructure (config, database, logging, middleware, health, exceptions)
├── shared/         # Cross-feature utilities (pagination, timestamps, error schemas)
├── main.py         # FastAPI application entry point
└── <features>/     # Feature slices directly here (e.g., products/, orders/)
```

### Database

**SQLAlchemy Setup**

- Async engine with connection pooling (pool_size=5, max_overflow=10)
- Base class: `app.core.database.Base` (extends `DeclarativeBase`)
- Session dependency: `get_db()` from `app.core.database`
- All models should inherit `TimestampMixin` from `app.shared.models` for automatic `created_at`/`updated_at`

**Migration Workflow**

1. Define/modify models inheriting from `Base` and `TimestampMixin`
2. Run `uv run alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Apply: `uv run alembic upgrade head`

### Logging

**Philosophy:** Logs are optimized for AI agent consumption. Include enough context for an LLM to understand and fix issues without human intervention.

**Structured Logging (structlog)**

- JSON output optimized for AI parsing
- Request ID correlation via `contextvars`
- Logger: `from app.core.logging import get_logger; logger = get_logger(__name__)`
- Event naming: `domain.component.action_state` pattern
- Exception logging: Always use `exc_info=True` for stack traces

**Event Pattern:** `{domain}.{component}.{action}_{state}`
- Examples: `user.registration_completed`, `database.connection_initialized`, `request.http_received`
- **Complete taxonomy and guidelines:** See `docs/standards/logging-standard.md`

**Middleware**

- `RequestLoggingMiddleware`: Logs all requests with correlation IDs
- `CORSMiddleware`: Configured for local development
- Adds `X-Request-ID` header to all responses

### Documentation Style

**Google-style Docstrings**

Use Google-style docstrings for all functions, classes, and modules:

```python
def process_request(user_id: str, query: str) -> dict[str, Any]:
    """Process a user request and return results.

    Args:
        user_id: Unique identifier for the user.
        query: The search query string.

    Returns:
        Dictionary containing results and metadata.

    Raises:
        ValueError: If query is empty or invalid.
    """
```

**YAML Front Matter (REQUIRED)**

All documentation files MUST include YAML front matter following our schema:

```yaml
---
type: standard              # task | command | adr | guide | spec | standard | learning
description: string         # one-line purpose
tags: [string]             # discovery keywords
---
```

- `type`: Document type (see `docs/standards/yaml-frontmatter.md` for taxonomy)
- `description`: Concise one-line summary of document purpose
- `tags`: Keywords for discoverability and filtering
- **Full schema and examples:** See `docs/standards/yaml-frontmatter.md`

### Shared Utilities

**Pagination** (`app.shared.schemas`)

- `PaginationParams`: Query params with `.offset` property
- `PaginatedResponse[T]`: Generic response with `.total_pages` property

**Timestamps** (`app.shared.models`)

- `TimestampMixin`: Adds `created_at` and `updated_at` columns
- `utcnow()`: Timezone-aware UTC datetime helper

**Error Handling** (`app.shared.schemas`, `app.core.exceptions`)

- `ErrorResponse`: Standard error response format
- Global exception handlers configured in `app.main`

### Configuration

- Environment variables via Pydantic Settings (`app.core.config`)
- Required: `DATABASE_URL` (postgresql+asyncpg://...)
- Copy `.env.example` to `.env` for local development
- Settings singleton: `get_settings()` from `app.core.config`

## Development Guidelines

**When Creating New Features**

1. Create feature directory directly under `app/` (e.g., `app/products/`)
2. Structure: `models.py`, `schemas.py`, `routes.py`, `service.py`, `tests/`
3. Models inherit from `Base` and `TimestampMixin`
4. Use `get_db()` dependency for database sessions
5. Follow structured logging: See `docs/standards/logging-standard.md` for event patterns
6. Add router to `app/main.py`: `app.include_router(feature_router)`

**Type Checking**

- Run both MyPy and Pyright before committing (both must pass)
- See `docs/standards/mypy-standard.md` and `docs/standards/pyright-standard.md` for configuration details
- No suppressions (`# type: ignore`, `# pyright: ignore`) unless absolutely necessary
- Document any suppressions with inline comments explaining why

**Testing**

- Write tests alongside feature code in `tests/` subdirectory
- Use `@pytest.mark.integration` for tests requiring database
- Fast execution preferred (~40 tests in <1s)
- Test fixtures in `app/tests/conftest.py`
- See `docs/standards/pytest-standard.md` for testing standards

**Logging**

- Use structured logging with context: `logger.info("feature.action_state", **context)`
- Include IDs, durations, error details
- Standard states: `_started`, `_completed`, `_failed`, `_validated`, `_rejected`
- **Full guidelines:** See `docs/standards/logging-standard.md`

**Database Patterns**

- Always use async/await with SQLAlchemy
- Use `select()` instead of `.query()` (SQLAlchemy 2.0 style)
- Test database operations with `@pytest.mark.integration`

**API Patterns**

- Health checks: `/health`, `/health/db`, `/health/ready`
- Pagination: Use `PaginationParams` and `PaginatedResponse[T]`
- Error responses: Use `ErrorResponse` schema
- Route prefixes: Use router `prefix` parameter for feature namespacing
