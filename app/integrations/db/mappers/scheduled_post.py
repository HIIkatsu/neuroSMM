"""
Mapper between :class:`ScheduledPostORM` and the domain :class:`ScheduledPost`.
"""

from __future__ import annotations

from app.domain.enums import ScheduleStatus
from app.domain.schedule import ScheduledPost
from app.integrations.db.models.scheduled_post import ScheduledPostORM
from app.integrations.db.utils import ensure_utc, ensure_utc_optional


def scheduled_post_to_domain(orm: ScheduledPostORM) -> ScheduledPost:
    """Convert an ORM row to a domain ``ScheduledPost``."""
    return ScheduledPost(
        id=orm.id,
        draft_id=orm.draft_id,
        project_id=orm.project_id,
        publish_at=ensure_utc(orm.publish_at),
        status=ScheduleStatus(orm.status),
        failure_reason=orm.failure_reason,
        published_at=ensure_utc_optional(orm.published_at),
        created_at=ensure_utc(orm.created_at),
        updated_at=ensure_utc(orm.updated_at),
    )


def scheduled_post_to_orm(domain: ScheduledPost) -> ScheduledPostORM:
    """Convert a domain ``ScheduledPost`` to an ORM instance (detached)."""
    orm = ScheduledPostORM(
        draft_id=domain.draft_id,
        project_id=domain.project_id,
        publish_at=domain.publish_at,
        status=domain.status.value,
        failure_reason=domain.failure_reason,
        published_at=domain.published_at,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )
    if domain.id is not None:
        orm.id = domain.id
    return orm
