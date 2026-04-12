"""Tests for Draft domain entity."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ConflictError, ValidationError
from app.domain.draft import Draft
from app.domain.enums import ContentType, DraftStatus, Tone


class TestDraftCreation:
    """Draft construction and defaults."""

    def test_minimal_draft(self) -> None:
        draft = Draft(project_id=1, author_id=1)
        assert draft.project_id == 1
        assert draft.author_id == 1
        assert draft.id is None
        assert draft.title == ""
        assert draft.text_content == ""
        assert draft.image_url is None
        assert draft.content_type == ContentType.TEXT
        assert draft.tone == Tone.NEUTRAL
        assert draft.status == DraftStatus.DRAFT
        assert draft.topic == ""

    def test_full_draft(self) -> None:
        draft = Draft(
            id=10,
            project_id=2,
            author_id=3,
            title="My Post",
            text_content="Hello world",
            tone=Tone.CASUAL,
            topic="Tech news",
        )
        assert draft.id == 10
        assert draft.title == "My Post"
        assert draft.text_content == "Hello world"
        assert draft.tone == Tone.CASUAL


class TestDraftValidation:
    """Draft invariants."""

    def test_project_id_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            Draft(project_id=0, author_id=1)

    def test_author_id_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            Draft(project_id=1, author_id=0)

    def test_title_stripped(self) -> None:
        draft = Draft(project_id=1, author_id=1, title="  My Post  ")
        assert draft.title == "My Post"

    def test_text_content_stripped(self) -> None:
        draft = Draft(project_id=1, author_id=1, text_content="  hello  ")
        assert draft.text_content == "hello"

    def test_title_max_length(self) -> None:
        with pytest.raises(PydanticValidationError):
            Draft(project_id=1, author_id=1, title="x" * 301)

    def test_text_content_max_length(self) -> None:
        with pytest.raises(PydanticValidationError):
            Draft(project_id=1, author_id=1, text_content="x" * 10_001)


class TestDraftImmutability:
    """Draft model is frozen."""

    def test_cannot_mutate(self) -> None:
        draft = Draft(project_id=1, author_id=1)
        with pytest.raises(PydanticValidationError):
            draft.status = DraftStatus.READY  # type: ignore[misc]


class TestDraftStateTransitions:
    """Draft lifecycle state machine."""

    def test_draft_to_ready(self) -> None:
        draft = Draft(project_id=1, author_id=1, text_content="Content")
        ready = draft.mark_ready()
        assert ready.status == DraftStatus.READY
        assert draft.status == DraftStatus.DRAFT  # original unchanged

    def test_ready_to_published(self) -> None:
        draft = Draft(
            project_id=1, author_id=1, text_content="Content", status=DraftStatus.READY
        )
        published = draft.mark_published()
        assert published.status == DraftStatus.PUBLISHED

    def test_ready_back_to_draft(self) -> None:
        draft = Draft(
            project_id=1, author_id=1, text_content="Content", status=DraftStatus.READY
        )
        back = draft.send_back_to_draft()
        assert back.status == DraftStatus.DRAFT

    def test_draft_to_archived(self) -> None:
        draft = Draft(project_id=1, author_id=1)
        archived = draft.archive()
        assert archived.status == DraftStatus.ARCHIVED

    def test_ready_to_archived(self) -> None:
        draft = Draft(
            project_id=1, author_id=1, text_content="Content", status=DraftStatus.READY
        )
        archived = draft.archive()
        assert archived.status == DraftStatus.ARCHIVED

    def test_published_cannot_transition(self) -> None:
        draft = Draft(
            project_id=1, author_id=1, text_content="X", status=DraftStatus.PUBLISHED
        )
        with pytest.raises(ConflictError):
            draft.archive()

    def test_archived_cannot_transition(self) -> None:
        draft = Draft(project_id=1, author_id=1, status=DraftStatus.ARCHIVED)
        with pytest.raises(ConflictError):
            draft.mark_ready()

    def test_draft_to_published_not_allowed(self) -> None:
        """Cannot skip READY and go directly from DRAFT to PUBLISHED."""
        draft = Draft(project_id=1, author_id=1, text_content="Content")
        with pytest.raises(ConflictError):
            draft.mark_published()

    def test_mark_ready_requires_content(self) -> None:
        """Empty draft cannot be marked ready."""
        draft = Draft(project_id=1, author_id=1)
        with pytest.raises(ValidationError, match="text or image"):
            draft.mark_ready()

    def test_mark_ready_with_image_only(self) -> None:
        """Draft with only an image can be marked ready."""
        draft = Draft(
            project_id=1,
            author_id=1,
            image_url="https://example.com/img.png",
            content_type=ContentType.IMAGE,
        )
        ready = draft.mark_ready()
        assert ready.status == DraftStatus.READY


class TestDraftContentMutation:
    """Content update helpers."""

    def test_update_text(self) -> None:
        draft = Draft(project_id=1, author_id=1, text_content="Old")
        updated = draft.update_text("New text")
        assert updated.text_content == "New text"
        assert draft.text_content == "Old"

    def test_update_text_strips(self) -> None:
        draft = Draft(project_id=1, author_id=1)
        updated = draft.update_text("  trimmed  ")
        assert updated.text_content == "trimmed"

    def test_cannot_update_text_when_published(self) -> None:
        draft = Draft(
            project_id=1, author_id=1, text_content="X", status=DraftStatus.PUBLISHED
        )
        with pytest.raises(ConflictError):
            draft.update_text("New")

    def test_cannot_update_text_when_archived(self) -> None:
        draft = Draft(project_id=1, author_id=1, status=DraftStatus.ARCHIVED)
        with pytest.raises(ConflictError):
            draft.update_text("New")

    def test_attach_image(self) -> None:
        draft = Draft(project_id=1, author_id=1)
        with_image = draft.attach_image("https://example.com/img.png")
        assert with_image.image_url == "https://example.com/img.png"
        assert draft.image_url is None

    def test_cannot_attach_image_when_published(self) -> None:
        draft = Draft(
            project_id=1, author_id=1, text_content="X", status=DraftStatus.PUBLISHED
        )
        with pytest.raises(ConflictError):
            draft.attach_image("https://example.com/img.png")

    def test_update_topic(self) -> None:
        draft = Draft(project_id=1, author_id=1)
        updated = draft.update_topic("AI news")
        assert updated.topic == "AI news"

    def test_cannot_update_topic_when_archived(self) -> None:
        draft = Draft(project_id=1, author_id=1, status=DraftStatus.ARCHIVED)
        with pytest.raises(ConflictError):
            draft.update_topic("New topic")
