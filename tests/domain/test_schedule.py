"""Tests for ScheduledPost domain entity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ConflictError, ValidationError
from app.domain.enums import ScheduleStatus
from app.domain.schedule import ScheduledPost


def _future(minutes: int = 30) -> datetime:
    """Return a UTC datetime *minutes* in the future."""
    return datetime.now(UTC) + timedelta(minutes=minutes)


def _past(minutes: int = 30) -> datetime:
    """Return a UTC datetime *minutes* in the past."""
    return datetime.now(UTC) - timedelta(minutes=minutes)


class TestScheduledPostCreation:
    """ScheduledPost construction and defaults."""

    def test_minimal(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=2, publish_at=_future())
        assert post.draft_id == 1
        assert post.project_id == 2
        assert post.id is None
        assert post.status == ScheduleStatus.PENDING
        assert post.failure_reason is None
        assert post.published_at is None

    def test_full(self) -> None:
        publish_time = _future(60)
        post = ScheduledPost(
            id=5,
            draft_id=10,
            project_id=3,
            publish_at=publish_time,
        )
        assert post.id == 5
        assert post.publish_at == publish_time


class TestScheduledPostValidation:
    """ScheduledPost invariants."""

    def test_draft_id_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            ScheduledPost(draft_id=0, project_id=1, publish_at=_future())

    def test_project_id_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            ScheduledPost(draft_id=1, project_id=0, publish_at=_future())

    def test_publish_at_must_be_timezone_aware(self) -> None:
        with pytest.raises(PydanticValidationError, match="timezone-aware"):
            ScheduledPost(
                draft_id=1,
                project_id=1,
                publish_at=datetime(2030, 1, 1),  # naive
            )

    def test_validate_publish_time_rejects_past(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_past())
        with pytest.raises(ValidationError, match="future"):
            post.validate_publish_time()

    def test_validate_publish_time_accepts_future(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future())
        post.validate_publish_time()  # should not raise


class TestScheduledPostImmutability:
    """ScheduledPost model is frozen."""

    def test_cannot_mutate(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future())
        with pytest.raises(PydanticValidationError):
            post.status = ScheduleStatus.PUBLISHED  # type: ignore[misc]


class TestScheduledPostTransitions:
    """ScheduledPost lifecycle state machine."""

    def test_pending_to_published(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future())
        published = post.mark_published()
        assert published.status == ScheduleStatus.PUBLISHED
        assert published.published_at is not None

    def test_pending_to_failed(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future())
        failed = post.mark_failed("API timeout")
        assert failed.status == ScheduleStatus.FAILED
        assert failed.failure_reason == "API timeout"

    def test_pending_to_cancelled(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future())
        cancelled = post.cancel()
        assert cancelled.status == ScheduleStatus.CANCELLED

    def test_published_cannot_transition(self) -> None:
        post = ScheduledPost(
            draft_id=1, project_id=1, publish_at=_future(), status=ScheduleStatus.PUBLISHED
        )
        with pytest.raises(ConflictError):
            post.cancel()

    def test_cancelled_cannot_transition(self) -> None:
        post = ScheduledPost(
            draft_id=1, project_id=1, publish_at=_future(), status=ScheduleStatus.CANCELLED
        )
        with pytest.raises(ConflictError):
            post.mark_published()

    def test_failed_to_pending_retry(self) -> None:
        post = ScheduledPost(
            draft_id=1,
            project_id=1,
            publish_at=_future(),
            status=ScheduleStatus.FAILED,
            failure_reason="timeout",
        )
        new_time = _future(60)
        retried = post.retry(new_time)
        assert retried.status == ScheduleStatus.PENDING
        assert retried.publish_at == new_time
        assert retried.failure_reason is None

    def test_retry_only_from_failed(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future())
        with pytest.raises(ConflictError):
            post.retry(_future(60))

    def test_retry_requires_tz_aware_time(self) -> None:
        post = ScheduledPost(
            draft_id=1,
            project_id=1,
            publish_at=_future(),
            status=ScheduleStatus.FAILED,
        )
        with pytest.raises(ValidationError, match="timezone-aware"):
            post.retry(datetime(2030, 1, 1))  # naive

    def test_mark_failed_requires_reason(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future())
        with pytest.raises(ValidationError, match="reason"):
            post.mark_failed("")

    def test_mark_failed_strips_reason(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future())
        failed = post.mark_failed("  timeout  ")
        assert failed.failure_reason == "timeout"


class TestScheduledPostIsDue:
    """is_due() domain query."""

    def test_is_due_when_past_publish_time(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_past())
        assert post.is_due() is True

    def test_not_due_when_future_publish_time(self) -> None:
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=_future(60))
        assert post.is_due() is False

    def test_not_due_when_not_pending(self) -> None:
        post = ScheduledPost(
            draft_id=1,
            project_id=1,
            publish_at=_past(),
            status=ScheduleStatus.PUBLISHED,
        )
        assert post.is_due() is False

    def test_is_due_with_explicit_now(self) -> None:
        publish_at = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
        post = ScheduledPost(draft_id=1, project_id=1, publish_at=publish_at)
        check_time = datetime(2025, 6, 1, 13, 0, tzinfo=UTC)
        assert post.is_due(now=check_time) is True
