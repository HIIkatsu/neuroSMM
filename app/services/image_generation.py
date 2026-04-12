"""Image generation service — orchestrates draft-based image generation.

Coordinates draft ownership verification, prompt building, provider call,
and draft update.  Business logic lives here, not in the router.
"""

from __future__ import annotations

from app.core.exceptions import AuthorizationError, ExternalServiceError, ValidationError
from app.domain.draft import Draft
from app.domain.enums import DraftStatus
from app.domain.generation import GenerationResult
from app.generation.image.prompt_builder import build_image_prompt
from app.generation.image.provider import ImageGenerationProvider
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository


class ImageGenerationService:
    """Service for generating images for drafts.

    Responsibilities:
    - Verify draft ownership through project access
    - Build an image prompt from draft context
    - Call the image generation provider
    - Apply the generated image URL back to the draft
    """

    def __init__(
        self,
        draft_repo: DraftRepository,
        project_repo: ProjectRepository,
        image_provider: ImageGenerationProvider,
    ) -> None:
        self._draft_repo = draft_repo
        self._project_repo = project_repo
        self._image_provider = image_provider

    async def generate_image_for_draft(
        self,
        *,
        draft_id: int,
        user_id: int,
        size: str | None = None,
    ) -> tuple[Draft, GenerationResult]:
        """Generate an image for an existing draft.

        Steps:
        1. Fetch the draft and verify user owns the project.
        2. Validate draft is in an editable state.
        3. Build a prompt from draft context (+ project context if available).
        4. Call the image generation provider.
        5. If successful, attach the image URL to the draft.
        6. Return the updated draft and generation result.

        Parameters
        ----------
        draft_id:
            ID of the draft to generate an image for.
        user_id:
            ID of the user requesting generation (ownership check).
        size:
            Optional image size (e.g. '1024x1024').

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

        if project.owner_id != user_id:
            raise AuthorizationError("You do not have access to this project")

        # 2. Validate editable state
        if draft.status not in (DraftStatus.DRAFT, DraftStatus.READY):
            raise ValidationError(
                f"Cannot generate image for draft in '{draft.status}' status"
            )

        # 3. Build prompt
        prompt = build_image_prompt(draft, project=project)

        # 4. Call provider
        result = await self._image_provider.generate(prompt, size=size)

        # 5. Handle result
        if result.is_failure:
            raise ExternalServiceError(
                result.error_message or "Image generation failed"
            )

        if not result.content:
            raise ExternalServiceError("Image generation returned empty content")

        # 6. Apply generated image to draft
        updated_draft = draft.attach_image(result.content)
        saved_draft = await self._draft_repo.update(updated_draft)

        return saved_draft, result
