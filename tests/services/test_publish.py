"""Tests for the PublishService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AuthorizationError, ConflictError, ExternalServiceError
from app.domain.draft import Draft
from app.domain.enums import ContentType, DraftStatus, Tone
from app.domain.project import Project
from app.publishing.provider import PublishResult
from app.services.publish import PublishOutcome, PublishService


def _make_project(*, owner_id: int = 1, channel_id: str | None = None) -> Project:
    return Project(
        id=1,
        owner_id=owner_id,
        title="Test Project",
        platform_channel_id=channel_id,
    )


def _make_draft(
    *,
    draft_id: int = 10,
    project_id: int = 1,
    author_id: int = 1,
    status: DraftStatus = DraftStatus.READY,
    title: str = "Test Draft",
    text_content: str = "Post content",
    image_url: str | None = None,
    content_type: ContentType = ContentType.TEXT,
    tone: Tone = Tone.NEUTRAL,
) -> Draft:
    return Draft(
        id=draft_id,
        project_id=project_id,
        author_id=author_id,
        status=status,
        title=title,
        text_content=text_content,
        image_url=image_url,
        content_type=content_type,
        tone=tone,
    )


def _build_service(
    *,
    draft: Draft | None = None,
    project: Project | None = None,
    publish_result: PublishResult | None = None,
) -> PublishService:
    """Build a PublishService with mocked repos and publisher."""
    draft_repo = AsyncMock()
    project_repo = AsyncMock()
    publisher = AsyncMock()

    if draft is not None:
        draft_repo.get_by_id.return_value = draft
        draft_repo.update.side_effect = lambda d: d

    if project is not None:
        project_repo.get_by_id.return_value = project

    if publish_result is not None:
        publisher.publish.return_value = publish_result

    return PublishService(draft_repo, project_repo, publisher)


class TestPublishDraft:
    """Tests for PublishService.publish_draft."""

    async def test_successful_publish(self) -> None:
        """Publish succeeds for a READY draft with a successful publisher."""
        draft = _make_draft(status=DraftStatus.READY)
        project = _make_project()
        result = PublishResult(success=True, platform_post_id="post-456")
        service = _build_service(draft=draft, project=project, publish_result=result)

        outcome = await service.publish_draft(draft_id=10, user_id=1)

        assert isinstance(outcome, PublishOutcome)
        assert outcome.success is True
        assert outcome.platform_post_id == "post-456"
        assert outcome.draft.status == DraftStatus.PUBLISHED

    async def test_draft_state_updated_to_published(self) -> None:
        """Draft transitions to PUBLISHED after successful publish."""
        draft = _make_draft(status=DraftStatus.READY)
        project = _make_project()
        result = PublishResult(success=True, platform_post_id="p-1")
        service = _build_service(draft=draft, project=project, publish_result=result)

        outcome = await service.publish_draft(draft_id=10, user_id=1)

        assert outcome.draft.status == DraftStatus.PUBLISHED
        # Verify repo update was called
        service._draft_repo.update.assert_called_once()  # type: ignore[union-attr]
        saved = service._draft_repo.update.call_args.args[0]  # type: ignore[union-attr]
        assert saved.status == DraftStatus.PUBLISHED

    async def test_ownership_enforced(self) -> None:
        """Publish is denied when user does not own the project."""
        draft = _make_draft(project_id=1)
        project = _make_project(owner_id=99)
        result = PublishResult(success=True)
        service = _build_service(draft=draft, project=project, publish_result=result)

        with pytest.raises(AuthorizationError):
            await service.publish_draft(draft_id=10, user_id=1)

    async def test_draft_status_not_ready_rejected(self) -> None:
        """Publish is denied when draft is in DRAFT status (not READY)."""
        draft = _make_draft(status=DraftStatus.DRAFT)
        project = _make_project()
        result = PublishResult(success=True)
        service = _build_service(draft=draft, project=project, publish_result=result)

        with pytest.raises(ConflictError, match="ready"):
            await service.publish_draft(draft_id=10, user_id=1)

    async def test_archived_draft_rejected(self) -> None:
        """Publish is denied for an archived draft."""
        draft = _make_draft(status=DraftStatus.ARCHIVED)
        project = _make_project()
        result = PublishResult(success=True)
        service = _build_service(draft=draft, project=project, publish_result=result)

        with pytest.raises(ConflictError, match="ready"):
            await service.publish_draft(draft_id=10, user_id=1)

    async def test_published_draft_rejected(self) -> None:
        """Publish is denied for an already-published draft."""
        draft = _make_draft(status=DraftStatus.PUBLISHED)
        project = _make_project()
        result = PublishResult(success=True)
        service = _build_service(draft=draft, project=project, publish_result=result)

        with pytest.raises(ConflictError, match="ready"):
            await service.publish_draft(draft_id=10, user_id=1)

    async def test_publisher_failure_raises_external_error(self) -> None:
        """Publisher failure produces ExternalServiceError with the reason."""
        draft = _make_draft(status=DraftStatus.READY)
        project = _make_project()
        result = PublishResult(success=False, error_message="Channel not found")
        service = _build_service(draft=draft, project=project, publish_result=result)

        with pytest.raises(ExternalServiceError, match="Channel not found"):
            await service.publish_draft(draft_id=10, user_id=1)

    async def test_publisher_failure_does_not_update_state(self) -> None:
        """Draft state is NOT changed when publisher fails."""
        draft = _make_draft(status=DraftStatus.READY)
        project = _make_project()
        result = PublishResult(success=False, error_message="Timeout")
        service = _build_service(draft=draft, project=project, publish_result=result)

        with pytest.raises(ExternalServiceError):
            await service.publish_draft(draft_id=10, user_id=1)

        # Verify update was NOT called
        service._draft_repo.update.assert_not_called()  # type: ignore[union-attr]

    async def test_publish_payload_includes_text_and_image(self) -> None:
        """Publisher receives the correct payload with text and image."""
        draft = _make_draft(
            text_content="Post body",
            image_url="https://img.test/pic.jpg",
        )
        project = _make_project(channel_id="@mychannel")
        result = PublishResult(success=True, platform_post_id="p-2")
        service = _build_service(draft=draft, project=project, publish_result=result)

        await service.publish_draft(draft_id=10, user_id=1)

        call_args = service._publisher.publish.call_args  # type: ignore[union-attr]
        payload = call_args.args[0]
        assert payload.text == "Post body"
        assert payload.image_url == "https://img.test/pic.jpg"
        assert payload.channel_id == "@mychannel"

    async def test_publish_response_correctness(self) -> None:
        """PublishOutcome fields are correct on success."""
        draft = _make_draft(draft_id=42, status=DraftStatus.READY)
        project = _make_project()
        result = PublishResult(success=True, platform_post_id="tg-789")
        service = _build_service(draft=draft, project=project, publish_result=result)

        outcome = await service.publish_draft(draft_id=42, user_id=1)

        assert outcome.draft.id == 42
        assert outcome.success is True
        assert outcome.platform_post_id == "tg-789"
        assert outcome.error_message is None
