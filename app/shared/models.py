"""Shared database models and mixins."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ARRAY, Boolean, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(UTC)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps.

    All models should inherit this mixin to automatically track
    when records are created and updated.

    Example:
        class Product(Base, TimestampMixin):
            __tablename__ = "products"
            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str] = mapped_column(String(200))
    """

    @declared_attr.directive
    def created_at(cls) -> Mapped[datetime]:
        """Timestamp when the record was created."""
        return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    @declared_attr.directive
    def updated_at(cls) -> Mapped[datetime]:
        """Timestamp when the record was last updated."""
        return mapped_column(
            DateTime(timezone=True),
            default=utcnow,
            onupdate=utcnow,
            nullable=False,
        )


class Company(Base, TimestampMixin):
    """Shared company model used by recruiting and jobs features."""

    __tablename__ = "shared_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    industries: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    num_employees: Mapped[int | None] = mapped_column(Integer)
    founded_on: Mapped[date | None] = mapped_column(Date)
    funding_stage: Mapped[str | None] = mapped_column(String(50))
    total_funding_usd: Mapped[int | None] = mapped_column(Integer)
    is_solara_56: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    blacklist_reason: Mapped[str | None] = mapped_column(String(100))


class OpenRouterModel(Base, TimestampMixin):
    """OpenRouter model pricing and metadata with snapshot history.

    Stores current state of OpenRouter models. Historical changes are tracked
    in OpenRouterModelChange table for audit and cost analysis.

    Example:
        model = OpenRouterModel(
            model_id="google/gemini-2.5-flash-lite",
            model_name="Gemini 2.5 Flash Lite",
            input_price=Decimal("0.10"),
            output_price=Decimal("0.40"),
            provider="google",
            performance_tier="lite",
        )
    """

    __tablename__ = "openrouter_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Pricing (per 1M tokens)
    input_price: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    output_price: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)

    # Capabilities
    context_window: Mapped[int] = mapped_column(Integer, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Classification
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    performance_tier: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Metadata (JSON for flexibility - benchmarks, notes, etc.)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class OpenRouterModelChange(Base, TimestampMixin):
    """Audit log of OpenRouter model changes.

    Tracks all detected changes: new models, price changes, deprecations.
    Used for weekly digests and historical cost analysis.

    Example:
        change = OpenRouterModelChange(
            model_id="google/gemini-2.5-flash-lite",
            change_type="price_decrease",
            field_changed="output_price",
            old_value="0.50",
            new_value="0.40",
            notified=False,
        )
    """

    __tablename__ = "openrouter_model_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Change details
    field_changed: Mapped[str | None] = mapped_column(String(50))
    old_value: Mapped[str | None] = mapped_column(String(255))
    new_value: Mapped[str | None] = mapped_column(String(255))

    # Detection metadata
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
