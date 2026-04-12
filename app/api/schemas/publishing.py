"""Preview and publish API request/response schemas.

These schemas are decoupled from domain models and publisher-specific objects.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ContentType, DraftStatus, Tone


class PreviewResponse(BaseModel):
    """Response schema for a draft preview."""

    draft_id: int = Field(..., description="ID of the previewed draft")
    project_id: int = Field(..., description="Owning project ID")
    title: str = Field(..., description="Draft title")
    text_content: str = Field(..., description="Draft text body")
    image_url: str | None = Field(None, description="Attached image URL")
    content_type: ContentType = Field(..., description="Kind of content")
    tone: Tone = Field(..., description="Writing tone")
    status: DraftStatus = Field(..., description="Current draft status")
    created_at: datetime = Field(..., description="Draft creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PublishResponse(BaseModel):
    """Response schema for a publish action."""

    draft_id: int = Field(..., description="ID of the published draft")
    status: DraftStatus = Field(..., description="Draft status after publish")
    platform_post_id: str | None = Field(
        None, description="Platform-assigned post ID"
    )
    published: bool = Field(..., description="Whether publishing succeeded")
