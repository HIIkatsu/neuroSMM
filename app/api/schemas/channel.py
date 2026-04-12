"""Channel binding API request/response schemas.

Decoupled from domain models and Telegram-specific types.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChannelBindRequest(BaseModel):
    """Request body for binding a Telegram channel to a project."""

    channel_identifier: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Telegram channel identifier (@username or numeric chat ID)",
    )


class ChannelBindResponse(BaseModel):
    """Response schema for a successful channel binding."""

    project_id: int = Field(..., description="ID of the project that was bound")
    channel_id: str = Field(..., description="Telegram chat ID that was bound")
    channel_title: str = Field(..., description="Title of the bound channel")
