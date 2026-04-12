"""Text generation API request/response schemas.

These schemas are decoupled from domain and provider-specific objects.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import GenerationStatus, GenerationType


class GenerateTextRequest(BaseModel):
    """Request body for generating text for a draft."""

    max_tokens: int | None = Field(
        default=None,
        gt=0,
        le=16_000,
        description="Optional token limit for text generation",
    )


class GenerationResultResponse(BaseModel):
    """Response schema for a generation result."""

    generation_type: GenerationType
    status: GenerationStatus
    content: str | None
    prompt_used: str
    model_name: str | None
    tokens_used: int | None
    created_at: datetime


class GenerateTextResponse(BaseModel):
    """Response schema for the generate-text endpoint.

    Contains both the updated draft and the generation result metadata.
    """

    draft_id: int
    draft_text_content: str
    generation: GenerationResultResponse
