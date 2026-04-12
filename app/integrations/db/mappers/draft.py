"""
Mapper between :class:`DraftORM` and the domain :class:`Draft`.
"""

from __future__ import annotations

from app.domain.draft import Draft
from app.domain.enums import ContentType, DraftStatus, Tone
from app.integrations.db.models.draft import DraftORM


def draft_to_domain(orm: DraftORM) -> Draft:
    """Convert an ORM row to a domain ``Draft``."""
    return Draft(
        id=orm.id,
        project_id=orm.project_id,
        author_id=orm.author_id,
        title=orm.title,
        text_content=orm.text_content,
        image_url=orm.image_url,
        content_type=ContentType(orm.content_type),
        tone=Tone(orm.tone),
        topic=orm.topic,
        status=DraftStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def draft_to_orm(domain: Draft) -> DraftORM:
    """Convert a domain ``Draft`` to an ORM instance (detached, not in session)."""
    orm = DraftORM(
        project_id=domain.project_id,
        author_id=domain.author_id,
        title=domain.title,
        text_content=domain.text_content,
        image_url=domain.image_url,
        content_type=domain.content_type.value,
        tone=domain.tone.value,
        topic=domain.topic,
        status=domain.status.value,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )
    if domain.id is not None:
        orm.id = domain.id
    return orm
