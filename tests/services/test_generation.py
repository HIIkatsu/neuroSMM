"""Tests for the TextGenerationService."""

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
from app.services.generation import TextGenerationService


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
    content_type: ContentType = ContentType.TEXT,
    text_content: str = "",
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
    )


def _success_result(*, content: str = "Generated text.") -> GenerationResult:
    return GenerationResult.success(
        generation_type=GenerationType.TEXT,
        content=content,
        prompt_used="test prompt",
        model_name="test-model",
        tokens_used=100,
    )


def _failure_result(*, error: str = "Provider error") -> GenerationResult:
    return GenerationResult.failure(
        generation_type=GenerationType.TEXT,
        error_message=error,
        prompt_used="test prompt",
        model_name="test-model",
    )


def _build_service(
    *,
    draft: Draft | None = None,
    project: Project | None = None,
    provider_result: GenerationResult | None = None,
) -> TextGenerationService:
    """Build a TextGenerationService with mocked repos and provider."""
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

    return TextGenerationService(draft_repo, project_repo, provider)


class TestGenerateTextForDraft:
    """Tests for TextGenerationService.generate_text_for_draft."""

    async def test_successful_generation(self) -> None:
        draft = _make_draft()
        project = _make_project()
        result = _success_result(content="Hello world!")
        service = _build_service(draft=draft, project=project, provider_result=result)

        updated_draft, gen_result = await service.generate_text_for_draft(
            draft_id=10, user_id=1
        )

        assert updated_draft.text_content == "Hello world!"
        assert gen_result.is_success
        assert gen_result.content == "Hello world!"

    async def test_draft_text_updated_via_domain_method(self) -> None:
        """Ensure generated text flows through Draft.update_text, not raw mutation."""
        draft = _make_draft(text_content="old text")
        project = _make_project()
        result = _success_result(content="new generated text")
        service = _build_service(draft=draft, project=project, provider_result=result)

        updated_draft, _ = await service.generate_text_for_draft(
            draft_id=10, user_id=1
        )

        assert updated_draft.text_content == "new generated text"

    async def test_ownership_enforced(self) -> None:
        draft = _make_draft(project_id=1)
        project = _make_project(owner_id=99)  # different owner
        service = _build_service(
            draft=draft, project=project, provider_result=_success_result()
        )

        with pytest.raises(AuthorizationError):
            await service.generate_text_for_draft(draft_id=10, user_id=1)

    async def test_archived_draft_rejected(self) -> None:
        draft = _make_draft(status=DraftStatus.ARCHIVED)
        project = _make_project()
        service = _build_service(
            draft=draft, project=project, provider_result=_success_result()
        )

        with pytest.raises(ValidationError, match="archived"):
            await service.generate_text_for_draft(draft_id=10, user_id=1)

    async def test_published_draft_rejected(self) -> None:
        draft = _make_draft(status=DraftStatus.PUBLISHED)
        project = _make_project()
        service = _build_service(
            draft=draft, project=project, provider_result=_success_result()
        )

        with pytest.raises(ValidationError, match="published"):
            await service.generate_text_for_draft(draft_id=10, user_id=1)

    async def test_ready_draft_allowed(self) -> None:
        """READY drafts can still have text generated."""
        draft = _make_draft(status=DraftStatus.READY, text_content="existing")
        project = _make_project()
        result = _success_result(content="improved text")
        service = _build_service(draft=draft, project=project, provider_result=result)

        updated_draft, gen_result = await service.generate_text_for_draft(
            draft_id=10, user_id=1
        )

        assert updated_draft.text_content == "improved text"
        assert gen_result.is_success

    async def test_provider_failure_raises_external_error(self) -> None:
        draft = _make_draft()
        project = _make_project()
        result = _failure_result(error="API timeout")
        service = _build_service(draft=draft, project=project, provider_result=result)

        with pytest.raises(ExternalServiceError, match="API timeout"):
            await service.generate_text_for_draft(draft_id=10, user_id=1)

    async def test_max_tokens_forwarded_to_provider(self) -> None:
        draft = _make_draft()
        project = _make_project()
        result = _success_result()
        service = _build_service(draft=draft, project=project, provider_result=result)

        await service.generate_text_for_draft(
            draft_id=10, user_id=1, max_tokens=500
        )

        # Verify the provider was called with max_tokens
        service._text_provider.generate.assert_called_once()  # type: ignore[union-attr]
        call_kwargs = service._text_provider.generate.call_args  # type: ignore[union-attr]
        assert call_kwargs.kwargs["max_tokens"] == 500

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

        await service.generate_text_for_draft(draft_id=10, user_id=1)

        # Check the prompt passed to the provider
        call_args = service._text_provider.generate.call_args  # type: ignore[union-attr]
        prompt = call_args.args[0]
        assert "My Title" in prompt
        assert "Python tips" in prompt
        assert "casual" in prompt.lower()

    async def test_draft_repo_update_called(self) -> None:
        """Verify that the updated draft is persisted."""
        draft = _make_draft()
        project = _make_project()
        result = _success_result(content="saved text")
        service = _build_service(draft=draft, project=project, provider_result=result)

        await service.generate_text_for_draft(draft_id=10, user_id=1)

        service._draft_repo.update.assert_called_once()  # type: ignore[union-attr]
        saved = service._draft_repo.update.call_args.args[0]  # type: ignore[union-attr]
        assert saved.text_content == "saved text"
