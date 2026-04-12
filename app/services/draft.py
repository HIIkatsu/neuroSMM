"""Draft service — business logic for draft use cases.

Operates on domain models, enforces ownership via project access,
delegates to repository.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import AuthorizationError
from app.domain.draft import Draft
from app.domain.enums import DraftStatus
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository


class DraftService:
    """Service for draft-related operations."""

    def __init__(
        self,
        draft_repo: DraftRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self._draft_repo = draft_repo
        self._project_repo = project_repo

    async def create_draft(
        self,
        *,
        project_id: int,
        author_id: int,
        title: str = "",
        text_content: str = "",
        content_type: str = "text",
        tone: str = "neutral",
        topic: str = "",
    ) -> Draft:
        """Create a new draft inside a project.

        Verifies that the user owns the project before creating the draft.

        Raises
        ------
        NotFoundError
            If the project does not exist.
        AuthorizationError
            If the user does not own the project.
        """
        await self._verify_project_access(project_id, author_id)

        from app.domain.enums import ContentType, Tone

        draft = Draft(
            project_id=project_id,
            author_id=author_id,
            title=title,
            text_content=text_content,
            content_type=ContentType(content_type),
            tone=Tone(tone),
            topic=topic,
        )
        return await self._draft_repo.create(draft)

    async def get_draft(
        self,
        *,
        draft_id: int,
        user_id: int,
    ) -> Draft:
        """Get a draft by ID, enforcing project ownership.

        Raises
        ------
        NotFoundError
            If the draft or its project does not exist.
        AuthorizationError
            If the user does not own the project.
        """
        draft = await self._draft_repo.get_by_id(draft_id)
        await self._verify_project_access(draft.project_id, user_id)
        return draft

    async def list_drafts(
        self,
        *,
        project_id: int,
        user_id: int,
        status: DraftStatus | None = None,
    ) -> list[Draft]:
        """List drafts for a project, enforcing ownership.

        Raises
        ------
        NotFoundError
            If the project does not exist.
        AuthorizationError
            If the user does not own the project.
        """
        await self._verify_project_access(project_id, user_id)
        return await self._draft_repo.list_by_project(project_id, status=status)

    async def update_draft(
        self,
        *,
        draft_id: int,
        user_id: int,
        title: str | None = None,
        text_content: str | None = None,
        topic: str | None = None,
    ) -> Draft:
        """Update a draft's basic fields, enforcing ownership.

        Raises
        ------
        NotFoundError
            If the draft or its project does not exist.
        AuthorizationError
            If the user does not own the project.
        """
        draft = await self._draft_repo.get_by_id(draft_id)
        await self._verify_project_access(draft.project_id, user_id)

        updates: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if title is not None:
            updates["title"] = title.strip()
        if text_content is not None:
            draft = draft.update_text(text_content)
        if topic is not None:
            draft = draft.update_topic(topic)

        if title is not None:
            draft = draft.model_copy(
                update={"title": title.strip(), "updated_at": datetime.now(UTC)}
            )

        return await self._draft_repo.update(draft)

    async def mark_ready(self, *, draft_id: int, user_id: int) -> Draft:
        """Transition a draft to READY status.

        Raises
        ------
        NotFoundError / AuthorizationError / ConflictError / ValidationError
        """
        draft = await self._draft_repo.get_by_id(draft_id)
        await self._verify_project_access(draft.project_id, user_id)
        ready = draft.mark_ready()
        return await self._draft_repo.update(ready)

    async def send_back_to_draft(self, *, draft_id: int, user_id: int) -> Draft:
        """Send a READY draft back to DRAFT status.

        Raises
        ------
        NotFoundError / AuthorizationError / ConflictError
        """
        draft = await self._draft_repo.get_by_id(draft_id)
        await self._verify_project_access(draft.project_id, user_id)
        back = draft.send_back_to_draft()
        return await self._draft_repo.update(back)

    async def archive_draft(self, *, draft_id: int, user_id: int) -> Draft:
        """Archive a draft.

        Raises
        ------
        NotFoundError / AuthorizationError / ConflictError
        """
        draft = await self._draft_repo.get_by_id(draft_id)
        await self._verify_project_access(draft.project_id, user_id)
        archived = draft.archive()
        return await self._draft_repo.update(archived)

    async def _verify_project_access(self, project_id: int, user_id: int) -> None:
        """Verify that the user owns the project.

        Raises
        ------
        NotFoundError
            If the project does not exist.
        AuthorizationError
            If the user does not own the project.
        """
        project = await self._project_repo.get_by_id(project_id)
        if project.owner_id != user_id:
            raise AuthorizationError("You do not have access to this project")
