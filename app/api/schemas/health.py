"""Health endpoint response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""

    status: str = Field(..., description="Overall health status")
    database: str = Field(..., description="Database connectivity status")
