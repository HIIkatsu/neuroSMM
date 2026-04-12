"""
User domain entity.

Represents the identity and profile of a NeuroSMM user.  The primary
identity is derived from Telegram (``telegram_id``), but the entity is
platform-agnostic at the domain level.

No I/O, no database coupling — pure Pydantic model.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class User(BaseModel):
    """Core user entity.

    Invariants
    ----------
    * ``telegram_id`` must be a positive integer (Telegram user IDs are always > 0).
    * ``username`` must be a non-empty stripped string when provided.
    * ``created_at`` defaults to *now* in UTC on construction.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = Field(default=None, description="Internal surrogate ID (assigned by DB)")
    telegram_id: int = Field(..., gt=0, description="Telegram user ID (always positive)")
    username: str | None = Field(
        default=None,
        description="Telegram username without leading @",
    )
    first_name: str = Field(
        default="",
        description="Telegram first name",
    )
    last_name: str | None = Field(
        default=None,
        description="Telegram last name",
    )
    language_code: str | None = Field(
        default=None,
        description="IETF language tag reported by Telegram client",
    )
    is_active: bool = Field(default=True, description="Soft-delete / deactivation flag")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ── validators ────────────────────────────────────────────────

    @field_validator("username", mode="before")
    @classmethod
    def _strip_username(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lstrip("@")
        return v if v else None

    @field_validator("first_name", mode="before")
    @classmethod
    def _strip_first_name(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    # ── domain helpers ────────────────────────────────────────────

    @property
    def display_name(self) -> str:
        """Human-readable display name, preferring username over first name."""
        if self.username:
            return f"@{self.username}"
        parts = [self.first_name]
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) or "Unknown"

    def deactivate(self) -> User:
        """Return a copy with ``is_active`` set to *False*."""
        return self.model_copy(update={"is_active": False, "updated_at": datetime.now(UTC)})

    def activate(self) -> User:
        """Return a copy with ``is_active`` set to *True*."""
        return self.model_copy(update={"is_active": True, "updated_at": datetime.now(UTC)})

    def with_updated_profile(
        self,
        *,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        """Return a copy with updated Telegram profile fields."""
        updates: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if username is not None:
            updates["username"] = username
        if first_name is not None:
            updates["first_name"] = first_name
        if last_name is not None:
            updates["last_name"] = last_name
        if language_code is not None:
            updates["language_code"] = language_code
        return self.model_copy(update=updates)
