"""Scheduling API routes.

Thin router — all orchestration lives in :class:`ScheduleService`.

Endpoints
---------
POST   /projects/{project_id}/drafts/{draft_id}/schedule
    Create a new scheduled post for a READY draft.

GET    /projects/{project_id}/schedules
    List all scheduled posts for a project.

POST   /projects/{project_id}/schedules/{schedule_id}/cancel
    Cancel a pending scheduled post.

POST   /projects/{project_id}/schedules/{schedule_id}/retry
    Retry a failed scheduled post with a new publish time.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db_session
from app.api.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleRetryRequest,
)
from app.core.config import get_settings
from app.domain.schedule import ScheduledPost
from app.domain.user import User
from app.integrations.telegram.client import TelegramClient
from app.publishing.provider import Publisher, StubPublisher
from app.publishing.telegram import TelegramPublisher
from app.services.schedule import ScheduleService, build_schedule_service

router = APIRouter(tags=["scheduling"])


def _get_publisher() -> Publisher:
    """Return the appropriate publisher based on configuration."""
    settings = get_settings()
    bot_token = settings.bot_token.get_secret_value()
    if bot_token:
        client = TelegramClient(bot_token)
        return TelegramPublisher(client)
    return StubPublisher()


def _get_schedule_service(
    session: AsyncSession = Depends(get_db_session),
) -> ScheduleService:
    return build_schedule_service(session, _get_publisher())


def _to_response(post: ScheduledPost) -> ScheduleResponse:
    assert post.id is not None
    return ScheduleResponse(
        id=post.id,
        draft_id=post.draft_id,
        project_id=post.project_id,
        publish_at=post.publish_at,
        status=post.status,
        failure_reason=post.failure_reason,
        published_at=post.published_at,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.post(
    "/projects/{project_id}/drafts/{draft_id}/schedule",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a draft for future publication",
)
async def create_schedule(
    project_id: int,
    draft_id: int,
    body: ScheduleCreateRequest,
    user: User = Depends(get_current_user),
    service: ScheduleService = Depends(_get_schedule_service),
) -> ScheduleResponse:
    """Schedule a READY draft for automatic publication at ``publish_at``."""
    assert user.id is not None
    post = await service.create_schedule(
        draft_id=draft_id,
        project_id=project_id,
        publish_at=body.publish_at,
        user_id=user.id,
    )
    return _to_response(post)


@router.get(
    "/projects/{project_id}/schedules",
    response_model=ScheduleListResponse,
    summary="List all scheduled posts for a project",
)
async def list_schedules(
    project_id: int,
    user: User = Depends(get_current_user),
    service: ScheduleService = Depends(_get_schedule_service),
) -> ScheduleListResponse:
    """Return all scheduled posts for the given project."""
    assert user.id is not None
    posts = await service.list_by_project(project_id=project_id, user_id=user.id)
    items = [_to_response(p) for p in posts]
    return ScheduleListResponse(items=items, count=len(items))


@router.post(
    "/projects/{project_id}/schedules/{schedule_id}/cancel",
    response_model=ScheduleResponse,
    summary="Cancel a pending scheduled post",
)
async def cancel_schedule(
    project_id: int,
    schedule_id: int,
    user: User = Depends(get_current_user),
    service: ScheduleService = Depends(_get_schedule_service),
) -> ScheduleResponse:
    """Cancel a PENDING scheduled post. Cannot cancel PUBLISHED or FAILED posts."""
    assert user.id is not None
    post = await service.cancel_schedule(schedule_id=schedule_id, user_id=user.id)
    return _to_response(post)


@router.post(
    "/projects/{project_id}/schedules/{schedule_id}/retry",
    response_model=ScheduleResponse,
    summary="Retry a failed scheduled post",
)
async def retry_schedule(
    project_id: int,
    schedule_id: int,
    body: ScheduleRetryRequest,
    user: User = Depends(get_current_user),
    service: ScheduleService = Depends(_get_schedule_service),
) -> ScheduleResponse:
    """Re-schedule a FAILED post for a new publish time."""
    assert user.id is not None
    post = await service.retry_schedule(
        schedule_id=schedule_id,
        user_id=user.id,
        new_publish_at=body.new_publish_at,
    )
    return _to_response(post)
