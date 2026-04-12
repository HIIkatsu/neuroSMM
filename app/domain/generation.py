"""
Generation Request and Result domain value objects.

These represent the input and output of an AI content generation cycle.
They are value objects — immutable, with no identity beyond their content.

No I/O, no database coupling — pure Pydantic model.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import GenerationStatus, GenerationType, Tone


class GenerationRequest(BaseModel):
    """Value object describing what the user wants generated.

    Invariants
    ----------
    * ``prompt`` must be a non-empty stripped string.
    * ``draft_id`` must be positive when provided (ties request to an existing draft).
    """

    model_config = ConfigDict(frozen=True)

    draft_id: int | None = Field(
        default=None,
        gt=0,
        description="Optional draft ID this generation is for",
    )
    generation_type: GenerationType = Field(
        ...,
        description="Whether to generate text or image",
    )
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The generation prompt / topic",
    )
    tone: Tone = Field(
        default=Tone.NEUTRAL,
        description="Desired tone for text generation",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        le=16_000,
        description="Optional token limit for text generation",
    )

    @field_validator("prompt", mode="before")
    @classmethod
    def _strip_prompt(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class GenerationResult(BaseModel):
    """Value object representing the outcome of an AI generation.

    Invariants
    ----------
    * ``content`` must be non-empty when status is COMPLETED.
    * ``error_message`` should be set when status is FAILED.
    """

    model_config = ConfigDict(frozen=True)

    generation_type: GenerationType = Field(
        ...,
        description="Type of content that was generated",
    )
    status: GenerationStatus = Field(
        default=GenerationStatus.PENDING,
        description="Outcome status of the generation",
    )
    content: str | None = Field(
        default=None,
        description="Generated text or image URL",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if generation failed",
    )
    prompt_used: str = Field(
        default="",
        description="The actual prompt sent to the AI provider",
    )
    model_name: str | None = Field(
        default=None,
        description="AI model identifier (e.g. 'gpt-4o', 'dall-e-3')",
    )
    tokens_used: int | None = Field(
        default=None,
        ge=0,
        description="Tokens consumed by this generation (if applicable)",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ── domain queries ────────────────────────────────────────────

    @property
    def is_success(self) -> bool:
        """True if generation completed successfully with content."""
        return self.status == GenerationStatus.COMPLETED and self.content is not None

    @property
    def is_failure(self) -> bool:
        """True if generation failed."""
        return self.status == GenerationStatus.FAILED

    # ── factory helpers ───────────────────────────────────────────

    @classmethod
    def success(
        cls,
        *,
        generation_type: GenerationType,
        content: str,
        prompt_used: str,
        model_name: str | None = None,
        tokens_used: int | None = None,
    ) -> GenerationResult:
        """Create a successful generation result."""
        return cls(
            generation_type=generation_type,
            status=GenerationStatus.COMPLETED,
            content=content,
            prompt_used=prompt_used,
            model_name=model_name,
            tokens_used=tokens_used,
        )

    @classmethod
    def failure(
        cls,
        *,
        generation_type: GenerationType,
        error_message: str,
        prompt_used: str,
        model_name: str | None = None,
    ) -> GenerationResult:
        """Create a failed generation result."""
        return cls(
            generation_type=generation_type,
            status=GenerationStatus.FAILED,
            content=None,
            error_message=error_message,
            prompt_used=prompt_used,
            model_name=model_name,
        )
