"""Text generation service — orchestrates draft-based text generation.

Coordinates draft ownership verification, prompt building, provider call,
and draft update. Business logic lives here, not in the router.
"""

from __future__ import annotations

from app.core.exceptions import ExternalServiceError, ValidationError
from app.domain.draft import Draft
from app.domain.enums import DraftStatus
from app.domain.generation import GenerationResult
from app.generation.text.prompt_builder import build_text_prompt
from app.generation.text.provider import TextGenerationProvider
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository


class TextGenerationService:
    """Service for generating text content for drafts.

    Responsibilities:
    - Verify draft ownership through project access
    - Build a prompt from draft context
    - Call the text generation provider
    - Apply the generated text back to the draft
    """

    def __init__(
        self,
        draft_repo: DraftRepository,
        project_repo: ProjectRepository,
        text_provider: TextGenerationProvider,
    ) -> None:
        self._draft_repo = draft_repo
        self._project_repo = project_repo
        self._text_provider = text_provider

    async def generate_text_for_draft(
        self,
        *,
        draft_id: int,
        user_id: int,
        max_tokens: int | None = None,
    ) -> tuple[Draft, GenerationResult]:
        """Generate text for an existing draft.

        Steps:
        1. Fetch the draft and verify user owns the project.
        2. Validate draft is in an editable state.
        3. Build a prompt from draft context (+ project context if available).
        4. Call the text generation provider.
        5. If successful, update the draft's text_content.
        6. Return the updated draft and generation result.

        Parameters
        ----------
        draft_id:
            ID of the draft to generate text for.
        user_id:
            ID of the user requesting generation (ownership check).
        max_tokens:
            Optional token limit for the generation.

        Returns
        -------
        tuple[Draft, GenerationResult]
            The updated draft and the generation result.

        Raises
        ------
        NotFoundError
            If draft or project does not exist.
        AuthorizationError
            If user does not own the project.
        ValidationError
            If draft is not in an editable state.
        ExternalServiceError
            If the generation provider fails.
        """
        # 1. Fetch draft and verify ownership
        draft = await self._draft_repo.get_by_id(draft_id)
        project = await self._project_repo.get_by_id(draft.project_id)

        from app.core.exceptions import AuthorizationError

        if project.owner_id != user_id:
            raise AuthorizationError("You do not have access to this project")

        # 2. Validate editable state
        if draft.status not in (DraftStatus.DRAFT, DraftStatus.READY):
            raise ValidationError(
                f"Cannot generate text for draft in '{draft.status}' status"
            )

        # 3. Build prompt
        prompt = build_text_prompt(draft, project=project)

        # 4. Call provider
        result = await self._text_provider.generate(prompt, max_tokens=max_tokens)

        # 5. Handle result
        if result.is_failure:
            raise ExternalServiceError(
                result.error_message or "Text generation failed"
            )

        # 6. Apply generated text to draft
        assert result.content is not None
        updated_draft = draft.update_text(result.content)
        saved_draft = await self._draft_repo.update(updated_draft)

        return saved_draft, result
