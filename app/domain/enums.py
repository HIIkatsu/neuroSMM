"""
Shared domain enumerations for NeuroSMM V2.

These enums define the finite state spaces used across domain entities.
They have no I/O dependencies — pure Python :class:`enum.StrEnum` only.
"""

from __future__ import annotations

from enum import StrEnum, unique

# ── content / post lifecycle ──────────────────────────────────────────


@unique
class DraftStatus(StrEnum):
    """Lifecycle states for a content draft.

    Transitions::

        DRAFT → READY → PUBLISHED
          │        │
          └────────┴──→ ARCHIVED
    """

    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@unique
class ScheduleStatus(StrEnum):
    """Lifecycle of a scheduled post.

    Transitions::

        PENDING → PUBLISHED
          │
          ├──→ FAILED
          └──→ CANCELLED
    """

    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── content classification ────────────────────────────────────────────


@unique
class ContentType(StrEnum):
    """Kind of content a draft represents."""

    TEXT = "text"
    IMAGE = "image"
    TEXT_AND_IMAGE = "text_and_image"


@unique
class Tone(StrEnum):
    """Desired writing tone for AI generation."""

    NEUTRAL = "neutral"
    FORMAL = "formal"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    PROMOTIONAL = "promotional"


# ── platform ──────────────────────────────────────────────────────────


@unique
class Platform(StrEnum):
    """Supported social-media publishing platforms."""

    TELEGRAM = "telegram"
    VK = "vk"


# ── generation ────────────────────────────────────────────────────────


@unique
class GenerationStatus(StrEnum):
    """Status of an AI generation request."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@unique
class GenerationType(StrEnum):
    """What kind of content is being generated."""

    TEXT = "text"
    IMAGE = "image"
