"""Tests for the PreviewService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AuthorizationError, ValidationError
from app.domain.draft import Draft
from app.domain.enums import ContentType, DraftStatus, Tone
from app.domain.project import Project
from app.services.preview import PreviewPayload, PreviewService


def _make_project(*, owner_id: int = 1) -> Project:
    return Project(id=1, owner_id=owner_id, title="Test Project")


def _make_draft(
    *,
    draft_id: int = 10,
    project_id: int = 1,
    author_id: int = 1,
    status: DraftStatus = DraftStatus.DRAFT,
    title: str = "Test Draft",
    text_content: str = "Hello world",
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
) -> PreviewService:
    """Build a PreviewService with mocked repos."""
    draft_repo = AsyncMock()
    project_repo = AsyncMock()

    if draft is not None:
        draft_repo.get_by_id.return_value = draft
    if project is not None:
        project_repo.get_by_id.return_value = project

    return PreviewService(draft_repo, project_repo)


class TestGetPreview:
    """Tests for PreviewService.get_preview."""

    async def test_successful_preview_draft_status(self) -> None:
        """Preview succeeds for a draft in DRAFT status."""
        draft = _make_draft(title="My Post", text_content="Content here")
        project = _make_project()
        service = _build_service(draft=draft, project=project)

        payload = await service.get_preview(draft_id=10, user_id=1)

        assert isinstance(payload, PreviewPayload)
        assert payload.draft_id == 10
        assert payload.title == "My Post"
        assert payload.text_content == "Content here"
        assert payload.status == DraftStatus.DRAFT

    async def test_successful_preview_ready_status(self) -> None:
        """Preview succeeds for a draft in READY status."""
        draft = _make_draft(status=DraftStatus.READY, text_content="Ready content")
        project = _make_project()
        service = _build_service(draft=draft, project=project)

        payload = await service.get_preview(draft_id=10, user_id=1)

        assert payload.status == DraftStatus.READY
        assert payload.text_content == "Ready content"

    async def test_preview_includes_image_reference(self) -> None:
        """Preview payload includes image URL when present."""
        draft = _make_draft(
            image_url="https://example.com/image.png",
            content_type=ContentType.TEXT_AND_IMAGE,
        )
        project = _make_project()
        service = _build_service(draft=draft, project=project)

        payload = await service.get_preview(draft_id=10, user_id=1)

        assert payload.image_url == "https://example.com/image.png"
        assert payload.content_type == ContentType.TEXT_AND_IMAGE

    async def test_preview_includes_metadata(self) -> None:
        """Preview payload includes tone and timestamps."""
        draft = _make_draft(tone=Tone.CASUAL)
        project = _make_project()
        service = _build_service(draft=draft, project=project)

        payload = await service.get_preview(draft_id=10, user_id=1)

        assert payload.tone == Tone.CASUAL
        assert payload.project_id == 1
        assert payload.created_at is not None
        assert payload.updated_at is not None

    async def test_ownership_enforced(self) -> None:
        """Preview is denied when user does not own the project."""
        draft = _make_draft(project_id=1)
        project = _make_project(owner_id=99)
        service = _build_service(draft=draft, project=project)

        with pytest.raises(AuthorizationError):
            await service.get_preview(draft_id=10, user_id=1)

    async def test_published_draft_rejected(self) -> None:
        """Preview is denied for a published draft."""
        draft = _make_draft(status=DraftStatus.PUBLISHED)
        project = _make_project()
        service = _build_service(draft=draft, project=project)

        with pytest.raises(ValidationError, match="published"):
            await service.get_preview(draft_id=10, user_id=1)

    async def test_archived_draft_rejected(self) -> None:
        """Preview is denied for an archived draft."""
        draft = _make_draft(status=DraftStatus.ARCHIVED)
        project = _make_project()
        service = _build_service(draft=draft, project=project)

        with pytest.raises(ValidationError, match="archived"):
            await service.get_preview(draft_id=10, user_id=1)

    async def test_response_correctness_all_fields(self) -> None:
        """All preview payload fields match the source draft."""
        draft = _make_draft(
            draft_id=42,
            project_id=5,
            title="Full Check",
            text_content="Full text",
            image_url="https://img.test/pic.jpg",
            content_type=ContentType.TEXT_AND_IMAGE,
            tone=Tone.HUMOROUS,
            status=DraftStatus.READY,
        )
        project = Project(id=5, owner_id=1, title="P")
        service = _build_service(draft=draft, project=project)

        payload = await service.get_preview(draft_id=42, user_id=1)

        assert payload.draft_id == 42
        assert payload.project_id == 5
        assert payload.title == "Full Check"
        assert payload.text_content == "Full text"
        assert payload.image_url == "https://img.test/pic.jpg"
        assert payload.content_type == ContentType.TEXT_AND_IMAGE
        assert payload.tone == Tone.HUMOROUS
        assert payload.status == DraftStatus.READY
