"""Text generation API route.

Thin router — all business logic lives in :class:`TextGenerationService`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db_session
from app.api.schemas.generation import (
    GenerateTextRequest,
    GenerateTextResponse,
    GenerationResultResponse,
)
from app.core.config import Settings, get_settings
from app.domain.user import User
from app.generation.text.provider import OpenAITextProvider, StubTextProvider
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.services.generation import TextGenerationService

router = APIRouter(
    prefix="/projects/{project_id}/drafts/{draft_id}/generate",
    tags=["generation"],
)


def _get_generation_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> TextGenerationService:
    draft_repo = DraftRepository(session)
    project_repo = ProjectRepository(session)

    api_key = settings.openai_api_key.get_secret_value()
    if api_key:
        provider = OpenAITextProvider(api_key=api_key)
    else:
        provider = StubTextProvider()  # type: ignore[assignment]

    return TextGenerationService(draft_repo, project_repo, provider)


@router.post(
    "/text",
    response_model=GenerateTextResponse,
    summary="Generate text for a draft",
)
async def generate_text(
    project_id: int,
    draft_id: int,
    body: GenerateTextRequest | None = None,
    user: User = Depends(get_current_user),
    service: TextGenerationService = Depends(_get_generation_service),
) -> GenerateTextResponse:
    """Generate text content for an existing draft.

    Uses the draft's title, topic, tone, and content type to build a prompt.
    The generated text is applied back to the draft's text_content field.

    Project ownership is enforced through the service layer.
    """
    assert user.id is not None
    max_tokens = body.max_tokens if body else None

    updated_draft, result = await service.generate_text_for_draft(
        draft_id=draft_id,
        user_id=user.id,
        max_tokens=max_tokens,
    )

    return GenerateTextResponse(
        draft_id=updated_draft.id,  # type: ignore[arg-type]
        draft_text_content=updated_draft.text_content,
        generation=GenerationResultResponse(
            generation_type=result.generation_type,
            status=result.status,
            content=result.content,
            prompt_used=result.prompt_used,
            model_name=result.model_name,
            tokens_used=result.tokens_used,
            created_at=result.created_at,
        ),
    )
