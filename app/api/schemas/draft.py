"""Draft API request/response schemas.

These schemas are decoupled from domain and ORM models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ContentType, DraftStatus, Tone


class DraftCreate(BaseModel):
    """Request body for creating a new draft."""

    title: str = Field(default="", max_length=300, description="Optional draft title")
    text_content: str = Field(default="", max_length=10_000, description="Main text body")
    content_type: ContentType = Field(default=ContentType.TEXT, description="Kind of content")
    tone: Tone = Field(default=Tone.NEUTRAL, description="Desired writing tone")
    topic: str = Field(default="", max_length=500, description="Generation topic hint")


class DraftUpdate(BaseModel):
    """Request body for updating a draft's basic fields."""

    title: str | None = Field(default=None, max_length=300, description="New draft title")
    text_content: str | None = Field(
        default=None, max_length=10_000, description="New text content"
    )
    topic: str | None = Field(default=None, max_length=500, description="New topic hint")


class DraftResponse(BaseModel):
    """Response schema for a single draft."""

    id: int
    project_id: int
    author_id: int
    title: str
    text_content: str
    image_url: str | None
    content_type: ContentType
    tone: Tone
    topic: str
    status: DraftStatus
    created_at: datetime
    updated_at: datetime


class DraftListResponse(BaseModel):
    """Response schema for a list of drafts."""

    items: list[DraftResponse]
    count: int
