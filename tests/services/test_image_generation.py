"""Tests for the ImageGenerationService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AuthorizationError, ExternalServiceError, ValidationError
from app.domain.draft import Draft
from app.domain.enums import (
    ContentType,
    DraftStatus,
    GenerationType,
    Tone,
)
from app.domain.generation import GenerationResult
from app.domain.project import Project
from app.services.image_generation import ImageGenerationService


def _make_project(*, owner_id: int = 1) -> Project:
    return Project(id=1, owner_id=owner_id, title="Test Project")


def _make_draft(
    *,
    draft_id: int = 10,
    project_id: int = 1,
    author_id: int = 1,
    status: DraftStatus = DraftStatus.DRAFT,
    title: str = "Test Draft",
    topic: str = "AI trends",
    tone: Tone = Tone.NEUTRAL,
    content_type: ContentType = ContentType.IMAGE,
    text_content: str = "",
    image_url: str | None = None,
) -> Draft:
    return Draft(
        id=draft_id,
        project_id=project_id,
        author_id=author_id,
        status=status,
        title=title,
        topic=topic,
        tone=tone,
        content_type=content_type,
        text_content=text_content,
        image_url=image_url,
    )


def _success_result(
    *, content: str = "https://example.com/generated-image.png",
) -> GenerationResult:
    return GenerationResult.success(
        generation_type=GenerationType.IMAGE,
        content=content,
        prompt_used="test prompt",
        model_name="test-model",
        tokens_used=None,
    )


def _failure_result(*, error: str = "Provider error") -> GenerationResult:
    return GenerationResult.failure(
        generation_type=GenerationType.IMAGE,
        error_message=error,
        prompt_used="test prompt",
        model_name="test-model",
    )


def _empty_result() -> GenerationResult:
    """Simulate a provider returning success status but no content."""
    return GenerationResult(
        generation_type=GenerationType.IMAGE,
        status="completed",  # type: ignore[arg-type]
        content=None,
        prompt_used="test prompt",
        model_name="test-model",
    )


def _build_service(
    *,
    draft: Draft | None = None,
    project: Project | None = None,
    provider_result: GenerationResult | None = None,
) -> ImageGenerationService:
    """Build an ImageGenerationService with mocked repos and provider."""
    draft_repo = AsyncMock()
    project_repo = AsyncMock()
    provider = AsyncMock()

    if draft is not None:
        draft_repo.get_by_id.return_value = draft
        # update returns whatever is passed (simulate save)
        draft_repo.update.side_effect = lambda d: d

    if project is not None:
        project_repo.get_by_id.return_value = project

    if provider_result is not None:
        provider.generate.return_value = provider_result

    return ImageGenerationService(draft_repo, project_repo, provider)


class TestGenerateImageForDraft:
    """Tests for ImageGenerationService.generate_image_for_draft."""

    async def test_successful_generation(self) -> None:
        draft = _make_draft()
        project = _make_project()
        result = _success_result(content="https://example.com/img.png")
        service = _build_service(draft=draft, project=project, provider_result=result)

        updated_draft, gen_result = await service.generate_image_for_draft(
            draft_id=10, user_id=1
        )

        assert updated_draft.image_url == "https://example.com/img.png"
        assert gen_result.is_success
        assert gen_result.content == "https://example.com/img.png"

    async def test_image_applied_via_domain_method(self) -> None:
        """Ensure generated image flows through Draft.attach_image, not raw mutation."""
        draft = _make_draft(image_url=None)
        project = _make_project()
        result = _success_result(content="https://example.com/new-image.png")
        service = _build_service(draft=draft, project=project, provider_result=result)

        updated_draft, _ = await service.generate_image_for_draft(
            draft_id=10, user_id=1
        )

        assert updated_draft.image_url == "https://example.com/new-image.png"

    async def test_replaces_existing_image(self) -> None:
        """If draft already has an image, generating replaces it."""
        draft = _make_draft(image_url="https://example.com/old.png")
        project = _make_project()
        result = _success_result(content="https://example.com/new.png")
        service = _build_service(draft=draft, project=project, provider_result=result)

        updated_draft, _ = await service.generate_image_for_draft(
            draft_id=10, user_id=1
        )

        assert updated_draft.image_url == "https://example.com/new.png"

    async def test_ownership_enforced(self) -> None:
        draft = _make_draft(project_id=1)
        project = _make_project(owner_id=99)  # different owner
        service = _build_service(
            draft=draft, project=project, provider_result=_success_result()
        )

        with pytest.raises(AuthorizationError):
            await service.generate_image_for_draft(draft_id=10, user_id=1)

    async def test_archived_draft_rejected(self) -> None:
        draft = _make_draft(status=DraftStatus.ARCHIVED)
        project = _make_project()
        service = _build_service(
            draft=draft, project=project, provider_result=_success_result()
        )

        with pytest.raises(ValidationError, match="archived"):
            await service.generate_image_for_draft(draft_id=10, user_id=1)

    async def test_published_draft_rejected(self) -> None:
        draft = _make_draft(status=DraftStatus.PUBLISHED)
        project = _make_project()
        service = _build_service(
            draft=draft, project=project, provider_result=_success_result()
        )

        with pytest.raises(ValidationError, match="published"):
            await service.generate_image_for_draft(draft_id=10, user_id=1)

    async def test_ready_draft_allowed(self) -> None:
        """READY drafts can still have images generated."""
        draft = _make_draft(
            status=DraftStatus.READY,
            text_content="some text",
            image_url="https://example.com/old.png",
        )
        project = _make_project()
        result = _success_result(content="https://example.com/improved.png")
        service = _build_service(draft=draft, project=project, provider_result=result)

        updated_draft, gen_result = await service.generate_image_for_draft(
            draft_id=10, user_id=1
        )

        assert updated_draft.image_url == "https://example.com/improved.png"
        assert gen_result.is_success

    async def test_provider_failure_raises_external_error(self) -> None:
        draft = _make_draft()
        project = _make_project()
        result = _failure_result(error="API timeout")
        service = _build_service(draft=draft, project=project, provider_result=result)

        with pytest.raises(
            ExternalServiceError, match="сгенерировать изображение|generation failed"
        ):
            await service.generate_image_for_draft(draft_id=10, user_id=1)

    async def test_empty_content_raises_external_error(self) -> None:
        """Provider returns success status but no image URL."""
        draft = _make_draft()
        project = _make_project()
        result = _empty_result()
        service = _build_service(draft=draft, project=project, provider_result=result)

        with pytest.raises(ExternalServiceError, match="пустой результат|empty content"):
            await service.generate_image_for_draft(draft_id=10, user_id=1)

    async def test_prompt_includes_draft_context(self) -> None:
        """Verify that prompt building uses draft fields."""
        draft = _make_draft(
            title="My Title",
            topic="Python tips",
            tone=Tone.CASUAL,
        )
        project = _make_project()
        result = _success_result()
        service = _build_service(draft=draft, project=project, provider_result=result)

        await service.generate_image_for_draft(draft_id=10, user_id=1)

        # Check the prompt passed to the provider
        call_args = service._image_provider.generate.call_args  # type: ignore[union-attr]
        prompt = call_args.args[0]
        assert "My Title" in prompt
        assert "Python tips" in prompt

    async def test_draft_text_included_in_prompt(self) -> None:
        """Verify existing draft text is included in image prompt for context."""
        draft = _make_draft(
            content_type=ContentType.TEXT_AND_IMAGE,
            text_content="Our latest product is amazing",
        )
        project = _make_project()
        result = _success_result()
        service = _build_service(draft=draft, project=project, provider_result=result)

        await service.generate_image_for_draft(draft_id=10, user_id=1)

        call_args = service._image_provider.generate.call_args  # type: ignore[union-attr]
        prompt = call_args.args[0]
        assert "Our latest product is amazing" in prompt

    async def test_draft_repo_update_called(self) -> None:
        """Verify that the updated draft is persisted."""
        draft = _make_draft()
        project = _make_project()
        result = _success_result(content="https://example.com/saved.png")
        service = _build_service(draft=draft, project=project, provider_result=result)

        await service.generate_image_for_draft(draft_id=10, user_id=1)

        service._draft_repo.update.assert_called_once()  # type: ignore[union-attr]
        saved = service._draft_repo.update.call_args.args[0]  # type: ignore[union-attr]
        assert saved.image_url == "https://example.com/saved.png"

    async def test_generation_result_type_is_image(self) -> None:
        """Verify the generation result is typed as IMAGE."""
        draft = _make_draft()
        project = _make_project()
        result = _success_result()
        service = _build_service(draft=draft, project=project, provider_result=result)

        _, gen_result = await service.generate_image_for_draft(
            draft_id=10, user_id=1
        )

        assert gen_result.generation_type == GenerationType.IMAGE
