"""Publish orchestration service.

Orchestrates the end-to-end publish flow: ownership check → state
validation → publish via publisher abstraction → state update on
success / failure-reason persistence on failure.

All ownership enforcement reuses the existing project-access pattern.
The publisher is injected via the :class:`Publisher` protocol so no
platform-specific objects leak into this layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import AuthorizationError, ConflictError, ExternalServiceError
from app.domain.draft import Draft
from app.domain.enums import DraftStatus
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.publishing.provider import Publisher, PublishPayload


@dataclass(frozen=True)
class PublishOutcome:
    """Result of the publish orchestration.

    Attributes
    ----------
    draft : Draft
        The draft after state transition (PUBLISHED on success, unchanged on failure).
    success : bool
        Whether publishing succeeded.
    platform_post_id : str | None
        Platform-assigned post ID (only on success).
    error_message : str | None
        Failure reason (only on failure).
    """

    draft: Draft
    success: bool
    platform_post_id: str | None = None
    error_message: str | None = None


class PublishService:
    """Orchestrates draft publishing through a publisher abstraction.

    Responsibilities:
    - Verify draft ownership through project access
    - Enforce that the draft is in READY state
    - Delegate publishing to the injected publisher
    - Transition draft to PUBLISHED on success
    - Persist failure reason on publisher failure
    """

    def __init__(
        self,
        draft_repo: DraftRepository,
        project_repo: ProjectRepository,
        publisher: Publisher,
    ) -> None:
        self._draft_repo = draft_repo
        self._project_repo = project_repo
        self._publisher = publisher

    async def publish_draft(
        self,
        *,
        draft_id: int,
        user_id: int,
    ) -> PublishOutcome:
        """Publish an existing draft.

        Parameters
        ----------
        draft_id:
            ID of the draft to publish.
        user_id:
            ID of the requesting user (ownership check).

        Returns
        -------
        PublishOutcome
            Contains the updated draft and publish result details.

        Raises
        ------
        NotFoundError
            If the draft or project does not exist.
        AuthorizationError
            If the user does not own the project.
        ConflictError
            If the draft is not in READY status.
        ExternalServiceError
            If the publisher fails and clean error propagation is needed.
        """
        # 1. Fetch draft and verify ownership
        draft = await self._draft_repo.get_by_id(draft_id)
        project = await self._project_repo.get_by_id(draft.project_id)

        if project.owner_id != user_id:
            raise AuthorizationError("You do not have access to this project")

        # 2. Enforce READY state
        if draft.status != DraftStatus.READY:
            raise ConflictError(
                f"Draft must be in 'ready' status to publish, "
                f"current status is '{draft.status}'"
            )

        # 3. Build payload and publish
        payload = PublishPayload(
            text=draft.text_content,
            image_url=draft.image_url,
            channel_id=project.platform_channel_id,
        )

        result = await self._publisher.publish(payload)

        # 4. Handle result
        if result.success:
            published_draft = draft.mark_published()
            saved_draft = await self._draft_repo.update(published_draft)
            return PublishOutcome(
                draft=saved_draft,
                success=True,
                platform_post_id=result.platform_post_id,
            )

        # 5. Publish failed — raise clean error
        raise ExternalServiceError(
            result.error_message or "Publishing failed"
        )
