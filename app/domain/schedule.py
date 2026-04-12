"""
Scheduled Post domain entity.

Represents a draft that is scheduled for future publication on a specific
channel.  The entity enforces invariants around publish timing and status
transitions.

No I/O, no database coupling — pure Pydantic model.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.exceptions import ConflictError, ValidationError
from app.domain.enums import ScheduleStatus

# ── allowed transitions ───────────────────────────────────────────────

_SCHEDULE_TRANSITIONS: dict[ScheduleStatus, frozenset[ScheduleStatus]] = {
    ScheduleStatus.PENDING: frozenset(
        {ScheduleStatus.PUBLISHED, ScheduleStatus.FAILED, ScheduleStatus.CANCELLED}
    ),
    ScheduleStatus.PUBLISHED: frozenset(),
    ScheduleStatus.FAILED: frozenset({ScheduleStatus.PENDING}),
    ScheduleStatus.CANCELLED: frozenset(),
}


class ScheduledPost(BaseModel):
    """A post that is scheduled for future publication.

    Invariants
    ----------
    * ``draft_id`` and ``project_id`` must be positive.
    * ``publish_at`` must be in the future at creation time (when validated).
    * Terminal states (PUBLISHED, CANCELLED) do not allow further transitions,
      except FAILED → PENDING for retry.
    """

    model_config = ConfigDict(frozen=True)

    id: int | None = Field(default=None, description="Internal surrogate ID (assigned by DB)")
    draft_id: int = Field(..., gt=0, description="ID of the draft to publish")
    project_id: int = Field(..., gt=0, description="ID of the target project / channel")

    publish_at: datetime = Field(
        ...,
        description="Scheduled publication time (must be UTC)",
    )
    status: ScheduleStatus = Field(
        default=ScheduleStatus.PENDING,
        description="Current schedule lifecycle status",
    )
    failure_reason: str | None = Field(
        default=None,
        description="Human-readable reason for failure, if applicable",
    )

    published_at: datetime | None = Field(
        default=None,
        description="Actual publication timestamp (set when published)",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ── validators ────────────────────────────────────────────────

    @field_validator("publish_at", mode="after")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        """Ensure publish_at has UTC timezone info."""
        if v.tzinfo is None:
            raise ValueError("publish_at must be timezone-aware (UTC)")
        return v

    # ── state transitions ─────────────────────────────────────────

    def _transition_to(self, target: ScheduleStatus) -> ScheduledPost:
        allowed = _SCHEDULE_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise ConflictError(
                f"Cannot transition scheduled post from '{self.status}' to '{target}'"
            )
        return self.model_copy(
            update={"status": target, "updated_at": datetime.now(UTC)},
        )

    def mark_published(self) -> ScheduledPost:
        """Mark this scheduled post as successfully published."""
        result = self._transition_to(ScheduleStatus.PUBLISHED)
        return result.model_copy(update={"published_at": datetime.now(UTC)})

    def mark_failed(self, reason: str) -> ScheduledPost:
        """Mark this scheduled post as failed with a reason."""
        if not reason.strip():
            raise ValidationError("Failure reason must be provided")
        result = self._transition_to(ScheduleStatus.FAILED)
        return result.model_copy(update={"failure_reason": reason.strip()})

    def cancel(self) -> ScheduledPost:
        """Cancel this scheduled post."""
        return self._transition_to(ScheduleStatus.CANCELLED)

    def retry(self, new_publish_at: datetime) -> ScheduledPost:
        """Re-schedule a failed post for a new time."""
        if self.status != ScheduleStatus.FAILED:
            raise ConflictError("Only failed scheduled posts can be retried")
        if new_publish_at.tzinfo is None:
            raise ValidationError("new_publish_at must be timezone-aware (UTC)")
        return self.model_copy(
            update={
                "status": ScheduleStatus.PENDING,
                "publish_at": new_publish_at,
                "failure_reason": None,
                "updated_at": datetime.now(UTC),
            },
        )

    # ── domain queries ────────────────────────────────────────────

    def is_due(self, now: datetime | None = None) -> bool:
        """Return True if the scheduled time has passed and the post is still pending."""
        if self.status != ScheduleStatus.PENDING:
            return False
        now = now or datetime.now(UTC)
        return now >= self.publish_at

    def validate_publish_time(self, now: datetime | None = None) -> None:
        """Raise :class:`ValidationError` if ``publish_at`` is in the past.

        Call this during creation — not enforced in the model itself because
        existing records loaded from DB may legitimately have past timestamps.
        """
        now = now or datetime.now(UTC)
        if self.publish_at <= now:
            raise ValidationError("Scheduled publish time must be in the future")
