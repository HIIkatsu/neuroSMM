"""
Content Draft domain entity.

A *Draft* represents a piece of content that a user is composing before
publishing.  It carries text and/or image content plus metadata needed to
track the content creation lifecycle.

The draft has a state machine:

    DRAFT → READY → PUBLISHED
      │        │
      └────────┴──→ ARCHIVED

Invariants are enforced by the transition methods.

No I/O, no database coupling — pure Pydantic model.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.exceptions import ConflictError, ValidationError
from app.domain.enums import ContentType, DraftStatus, Tone

# ── allowed transitions ───────────────────────────────────────────────

_DRAFT_TRANSITIONS: dict[DraftStatus, frozenset[DraftStatus]] = {
    DraftStatus.DRAFT: frozenset({DraftStatus.READY, DraftStatus.ARCHIVED}),
    DraftStatus.READY: frozenset({DraftStatus.DRAFT, DraftStatus.PUBLISHED, DraftStatus.ARCHIVED}),
    DraftStatus.PUBLISHED: frozenset(),
    DraftStatus.ARCHIVED: frozenset(),
}


class Draft(BaseModel):
    """Core content-draft entity.

    Invariants
    ----------
    * ``project_id`` must be positive.
    * ``title`` must be non-empty when provided (stripped).
    * A draft in ``PUBLISHED`` or ``ARCHIVED`` status cannot transition further.
    * ``content_type`` must match actual content fields (see model validator).
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = Field(default=None, description="Internal surrogate ID (assigned by DB)")
    project_id: int = Field(..., gt=0, description="Owning project ID")
    author_id: int = Field(..., gt=0, description="ID of the User who created this draft")

    title: str = Field(
        default="",
        max_length=300,
        description="Optional short title / headline for the post",
    )
    text_content: str = Field(
        default="",
        max_length=10_000,
        description="Main text body of the post",
    )
    image_url: str | None = Field(
        default=None,
        description="URL or storage key for the attached image",
    )

    content_type: ContentType = Field(
        default=ContentType.TEXT,
        description="Kind of content this draft represents",
    )
    tone: Tone = Field(
        default=Tone.NEUTRAL,
        description="Desired writing tone (used for AI generation context)",
    )
    topic: str = Field(
        default="",
        max_length=500,
        description="Generation topic / prompt hint",
    )

    status: DraftStatus = Field(
        default=DraftStatus.DRAFT,
        description="Current lifecycle status",
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ── validators ────────────────────────────────────────────────

    @field_validator("title", "text_content", "topic", mode="before")
    @classmethod
    def _strip_strings(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def _validate_content_type_matches_fields(self) -> Draft:
        """Ensure content_type is consistent with actual content fields."""
        has_text = bool(self.text_content)
        has_image = self.image_url is not None

        if self.content_type == ContentType.IMAGE and not has_image:
            if has_text and not has_image:
                # Text-only content but marked as IMAGE — that's inconsistent
                raise ValueError(
                    "content_type is 'image' but only text_content is provided"
                )
        if self.content_type == ContentType.TEXT_AND_IMAGE and not (has_text and has_image):
            # Allow partially filled during draft creation, but warn if
            # marking as READY
            pass

        return self

    # ── state transitions ─────────────────────────────────────────

    def _transition_to(self, target: DraftStatus) -> Draft:
        """Return a copy transitioned to *target*, or raise on invalid transition."""
        allowed = _DRAFT_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise ConflictError(
                f"Cannot transition draft from '{self.status}' to '{target}'"
            )
        return self.model_copy(
            update={"status": target, "updated_at": datetime.now(UTC)},
        )

    def mark_ready(self) -> Draft:
        """Transition to READY.

        Validates that the transition is allowed and content is non-empty.
        """
        # Check transition validity first (catches ARCHIVED/PUBLISHED states)
        allowed = _DRAFT_TRANSITIONS.get(self.status, frozenset())
        if DraftStatus.READY not in allowed:
            raise ConflictError(
                f"Cannot transition draft from '{self.status}' to '{DraftStatus.READY}'"
            )
        if not self.text_content and self.image_url is None:
            raise ValidationError("Draft must have text or image content before marking ready")
        return self._transition_to(DraftStatus.READY)

    def mark_published(self) -> Draft:
        """Transition from READY to PUBLISHED."""
        return self._transition_to(DraftStatus.PUBLISHED)

    def send_back_to_draft(self) -> Draft:
        """Return a READY draft back to DRAFT for further editing."""
        return self._transition_to(DraftStatus.DRAFT)

    def archive(self) -> Draft:
        """Archive the draft (terminal state from DRAFT or READY)."""
        return self._transition_to(DraftStatus.ARCHIVED)

    # ── content mutation helpers ──────────────────────────────────

    def update_text(self, text: str) -> Draft:
        """Return a copy with updated text content."""
        if self.status not in (DraftStatus.DRAFT, DraftStatus.READY):
            raise ConflictError(f"Cannot edit text in '{self.status}' status")
        return self.model_copy(
            update={
                "text_content": text.strip(),
                "updated_at": datetime.now(UTC),
            },
        )

    def attach_image(self, image_url: str) -> Draft:
        """Return a copy with an attached image."""
        if self.status not in (DraftStatus.DRAFT, DraftStatus.READY):
            raise ConflictError(f"Cannot attach image in '{self.status}' status")
        return self.model_copy(
            update={
                "image_url": image_url,
                "updated_at": datetime.now(UTC),
            },
        )

    def update_topic(self, topic: str) -> Draft:
        """Return a copy with an updated generation topic."""
        if self.status not in (DraftStatus.DRAFT, DraftStatus.READY):
            raise ConflictError(f"Cannot update topic in '{self.status}' status")
        return self.model_copy(
            update={
                "topic": topic.strip(),
                "updated_at": datetime.now(UTC),
            },
        )
