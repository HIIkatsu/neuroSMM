"""API schemas for scheduled-post endpoints.

Separate from domain models; no ORM types leak here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ScheduleStatus


class ScheduleCreateRequest(BaseModel):
    """Request body for creating a new scheduled post."""

    publish_at: datetime = Field(
        ...,
        description="UTC datetime when the draft should be published (must be in the future)",
    )


class ScheduleRetryRequest(BaseModel):
    """Request body for retrying a failed scheduled post."""

    new_publish_at: datetime = Field(
        ...,
        description="New UTC datetime for the rescheduled publication",
    )


class ScheduleResponse(BaseModel):
    """Response schema for a scheduled post."""

    id: int = Field(..., description="Scheduled post ID")
    draft_id: int = Field(..., description="ID of the draft being scheduled")
    project_id: int = Field(..., description="ID of the owning project")
    publish_at: datetime = Field(..., description="Scheduled publication time")
    status: ScheduleStatus = Field(..., description="Current schedule status")
    failure_reason: str | None = Field(None, description="Failure reason if status is FAILED")
    published_at: datetime | None = Field(None, description="Actual publication time if published")
    created_at: datetime = Field(..., description="When the schedule was created")
    updated_at: datetime = Field(..., description="When the schedule was last updated")
