"""
Mapper between :class:`ProjectORM` and the domain :class:`Project`.
"""

from __future__ import annotations

from app.domain.enums import Platform
from app.domain.project import Project
from app.integrations.db.models.project import ProjectORM
from app.integrations.db.utils import ensure_utc


def project_to_domain(orm: ProjectORM) -> Project:
    """Convert an ORM row to a domain ``Project``."""
    return Project(
        id=orm.id,
        owner_id=orm.owner_id,
        title=orm.title,
        description=orm.description,
        platform=Platform(orm.platform),
        platform_channel_id=orm.platform_channel_id,
        is_active=orm.is_active,
        created_at=ensure_utc(orm.created_at),
        updated_at=ensure_utc(orm.updated_at),
    )


def project_to_orm(domain: Project) -> ProjectORM:
    """Convert a domain ``Project`` to an ORM instance (detached, not in session)."""
    orm = ProjectORM(
        owner_id=domain.owner_id,
        title=domain.title,
        description=domain.description,
        platform=domain.platform.value,
        platform_channel_id=domain.platform_channel_id,
        is_active=domain.is_active,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )
    if domain.id is not None:
        orm.id = domain.id
    return orm
