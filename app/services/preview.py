"""Preview orchestration service.

Assembles a preview-ready representation of a draft by combining text,
image reference, and metadata.  Validates that the draft is in a
sensible state for preview.

All ownership enforcement reuses the existing project-access pattern
from :class:`DraftService`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.exceptions import AuthorizationError, ValidationError
from app.domain.draft import Draft
from app.domain.enums import ContentType, DraftStatus, Tone
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository


class PreviewPayload(BaseModel):
    """Preview-ready representation of a draft.

    Contains everything needed to render a preview in the client.
    This is a read-only value object — not persisted.
    """

    model_config = ConfigDict(frozen=True)

    draft_id: int
    project_id: int
    title: str
    text_content: str
    image_url: str | None
    content_type: ContentType
    tone: Tone
    status: DraftStatus
    created_at: datetime
    updated_at: datetime


# States from which preview is allowed
_PREVIEWABLE_STATES: frozenset[DraftStatus] = frozenset(
    {DraftStatus.DRAFT, DraftStatus.READY}
)


class PreviewService:
    """Orchestrates draft preview.

    Responsibilities:
    - Verify draft ownership through project access
    - Validate the draft is in a previewable state
    - Assemble and return a preview payload
    """

    def __init__(
        self,
        draft_repo: DraftRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self._draft_repo = draft_repo
        self._project_repo = project_repo

    async def get_preview(
        self,
        *,
        draft_id: int,
        user_id: int,
    ) -> PreviewPayload:
        """Build a preview for the given draft.

        Parameters
        ----------
        draft_id:
            ID of the draft to preview.
        user_id:
            ID of the requesting user (ownership check).

        Returns
        -------
        PreviewPayload
            A preview-ready representation of the draft.

        Raises
        ------
        NotFoundError
            If the draft or project does not exist.
        AuthorizationError
            If the user does not own the project.
        ValidationError
            If the draft is not in a previewable state.
        """
        draft = await self._draft_repo.get_by_id(draft_id)
        await self._verify_project_access(draft.project_id, user_id)
        self._validate_previewable(draft)
        return self._build_payload(draft)

    async def _verify_project_access(self, project_id: int, user_id: int) -> None:
        """Verify that the user owns the project."""
        project = await self._project_repo.get_by_id(project_id)
        if project.owner_id != user_id:
            raise AuthorizationError("У вас нет доступа к этому проекту")

    @staticmethod
    def _validate_previewable(draft: Draft) -> None:
        """Ensure the draft is in a state that allows preview."""
        if draft.status not in _PREVIEWABLE_STATES:
            raise ValidationError(
                f"Нельзя просмотреть черновик в статусе '{draft.status}'"
            )

    @staticmethod
    def _build_payload(draft: Draft) -> PreviewPayload:
        """Assemble a preview payload from a domain draft."""
        return PreviewPayload(
            draft_id=draft.id,  # type: ignore[arg-type]
            project_id=draft.project_id,
            title=draft.title,
            text_content=draft.text_content,
            image_url=draft.image_url,
            content_type=draft.content_type,
            tone=draft.tone,
            status=draft.status,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
        )
