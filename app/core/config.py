"""Application configuration using pydantic-settings.

This module provides centralized configuration management:
- Environment variable loading from .env file
- Type-safe settings with validation
- Cached settings instance with @lru_cache
- Settings for application, CORS, and future database configuration
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration.

    All settings can be overridden via environment variables.
    Environment variables are case-insensitive.
    Settings are loaded from .env file if present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Don't fail if .env file doesn't exist
        extra="ignore",
    )

    # Application metadata
    app_name: str = "AI Recruiter Pipeline"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"
    port: int = Field(default=8123, description="Server port (set by Render)")

    # Database
    database_url: str

    # CORS settings
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8123",
        "http://104.236.56.33:3000",  # DigitalOcean dashboard
        "https://air-dashboard-alc0.onrender.com",  # Render dashboard
        "https://air-api-yt5c.onrender.com",  # Render API
    ]

    # LLM Configuration
    openrouter_api_key: str = Field(default="", description="OpenRouter API key for LLM access")
    llm_model: str = Field(
        default="google/gemini-2.5-flash-lite",
        description="LLM model to use for classification and scoring",
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.0 = deterministic, 2.0 = creative)",
    )
    llm_max_tokens: int = Field(
        default=2048, ge=1, le=8192, description="Maximum tokens for LLM responses"
    )
    llm_timeout: float = Field(
        default=30.0, ge=1.0, le=300.0, description="Timeout for LLM API calls in seconds"
    )

    # Langfuse Observability Configuration
    langfuse_public_key: str = Field(default="", description="Langfuse public key")
    langfuse_secret_key: str = Field(default="", description="Langfuse secret key")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse host URL"
    )

    # LeadMagic API Configuration
    leadmagic_api_key: str = Field(
        default="", description="LeadMagic API key for company enrichment"
    )

    # Perplexity API Configuration
    perplexity_api_key: str = Field(
        default="", description="Perplexity API key for deep company enrichment"
    )

    # n8n Webhook for Email Notifications
    n8n_webhook_url: str = Field(
        default="",
        description="n8n webhook URL for email notifications",
    )

    # Slack Webhook for Notifications
    slack_webhook_url: str = Field(
        default="",
        description="Slack webhook URL for OpenRouter model monitoring notifications",
    )

    # Mailgun Configuration (HTTP API for email sending)
    mailgun_api_key: str = Field(default="", description="Mailgun API key")
    mailgun_domain: str = Field(
        default="",
        description="Mailgun domain (e.g., sandboxXXX.mailgun.org or your verified domain)",
    )
    digest_recipient: str = Field(default="", description="Email address for digest emails")

    # Scheduler Configuration
    scheduler_timezone: str = Field(
        default="Europe/London", description="Timezone for scheduler jobs"
    )
    scrape_hours: str = Field(
        default="5,17", description="Hours to run scrape jobs (comma-separated)"
    )
    digest_hours: str = Field(
        default="6", description="Hours to send digest emails Mon-Fri (comma-separated)"
    )

    # Dashboard Configuration
    dashboard_url: str = Field(
        default="http://localhost:3000",
        description="URL for the dashboard (used in digest emails)",
    )

    # File Logging Configuration
    log_file_enabled: bool = Field(default=True, description="Enable file logging with rotation")
    log_file_path: str = Field(
        default="logs/air.log", description="Log file path (relative to project root)"
    )
    log_file_max_bytes: int = Field(
        default=10_485_760, description="Max log file size in bytes (10MB default)"
    )
    log_file_backup_count: int = Field(default=5, description="Number of backup log files to keep")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    The @lru_cache decorator ensures settings are only loaded once
    and reused across the application lifecycle.

    Returns:
        The application settings instance.
    """
    # pydantic-settings automatically loads required fields (like database_url)
    # from environment variables at runtime. Mypy's static analysis doesn't understand
    # this behavior and expects all required fields as constructor arguments. This is
    # a known limitation of mypy with pydantic-settings. The call-arg error is suppressed
    # as the runtime behavior is correct and type-safe.
    return Settings()  # type: ignore[call-arg]
