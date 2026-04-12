"""Project API request/response schemas.

These schemas are decoupled from domain and ORM models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import Platform


class ProjectCreate(BaseModel):
    """Request body for creating a new project."""

    title: str = Field(..., min_length=1, max_length=200, description="Project title")
    description: str = Field(
        default="", max_length=2000, description="Optional project description"
    )
    platform: Platform = Field(
        default=Platform.TELEGRAM, description="Target publishing platform"
    )


class ProjectUpdate(BaseModel):
    """Request body for updating a project's basic fields."""

    title: str | None = Field(
        default=None, min_length=1, max_length=200, description="New project title"
    )
    description: str | None = Field(
        default=None, max_length=2000, description="New project description"
    )


class ProjectResponse(BaseModel):
    """Response schema for a single project."""

    id: int
    owner_id: int
    title: str
    description: str
    platform: Platform
    platform_channel_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Response schema for a list of projects."""

    items: list[ProjectResponse]
    count: int
