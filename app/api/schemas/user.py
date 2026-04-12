"""User and bootstrap API response schemas.

These schemas are decoupled from domain and ORM models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """Response schema for the current user."""

    id: int = Field(..., description="Internal user ID")
    telegram_id: int = Field(..., description="Telegram user ID")
    username: str | None = Field(None, description="Telegram username (without @)")
    first_name: str = Field(..., description="Telegram first name")
    last_name: str | None = Field(None, description="Telegram last name")
    language_code: str | None = Field(None, description="IETF language tag")
    is_active: bool = Field(..., description="Whether the account is active")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: datetime = Field(..., description="Last profile update time")


class AvailableFeatures(BaseModel):
    """Flags indicating which optional features are available."""

    text_generation: bool = Field(
        ..., description="Whether AI text generation is available"
    )
    image_generation: bool = Field(
        ..., description="Whether AI image generation is available"
    )


class BootstrapResponse(BaseModel):
    """Response schema for the Mini App bootstrap endpoint.

    Provides the current user identity and feature-availability flags
    so the Mini App shell can configure itself on startup.
    """

    user: UserResponse = Field(..., description="Current authenticated user")
    features: AvailableFeatures = Field(
        ..., description="Available platform features"
    )
