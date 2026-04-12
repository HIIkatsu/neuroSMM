"""
Project / Channel domain entity.

A *Project* is the user-facing wrapper around a publishing channel.  It
binds a user to a specific social-media channel and holds channel-level
configuration (platform, name, description, etc.).

No I/O, no database coupling — pure Pydantic model.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import Platform


class Project(BaseModel):
    """Core project entity (maps to a publishing channel).

    Invariants
    ----------
    * ``title`` must be a non-empty stripped string of at most 200 characters.
    * ``owner_id`` must be a positive integer referencing a :class:`User`.
    * ``platform`` must be a valid :class:`Platform` value.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = Field(default=None, description="Internal surrogate ID (assigned by DB)")
    owner_id: int = Field(..., gt=0, description="ID of the owning User")
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable project / channel name",
    )
    description: str = Field(
        default="",
        max_length=2000,
        description="Optional project description",
    )
    platform: Platform = Field(
        default=Platform.TELEGRAM,
        description="Target publishing platform",
    )
    platform_channel_id: str | None = Field(
        default=None,
        description="Platform-specific channel identifier (e.g. Telegram chat ID)",
    )
    is_active: bool = Field(default=True, description="Soft-delete / deactivation flag")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ── validators ────────────────────────────────────────────────

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("description", mode="before")
    @classmethod
    def _strip_description(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    # ── domain helpers ────────────────────────────────────────────

    def rename(self, new_title: str) -> Project:
        """Return a copy with a new title."""
        return self.model_copy(
            update={"title": new_title.strip(), "updated_at": datetime.now(UTC)},
        )

    def deactivate(self) -> Project:
        """Return a copy with ``is_active`` set to *False*."""
        return self.model_copy(update={"is_active": False, "updated_at": datetime.now(UTC)})

    def activate(self) -> Project:
        """Return a copy with ``is_active`` set to *True*."""
        return self.model_copy(update={"is_active": True, "updated_at": datetime.now(UTC)})

    def link_channel(self, platform_channel_id: str) -> Project:
        """Return a copy linked to a specific platform channel."""
        return self.model_copy(
            update={
                "platform_channel_id": platform_channel_id,
                "updated_at": datetime.now(UTC),
            },
        )
