"""
Mapper between :class:`UserORM` and the domain :class:`User`.
"""

from __future__ import annotations

from app.domain.user import User
from app.integrations.db.models.user import UserORM


def user_to_domain(orm: UserORM) -> User:
    """Convert an ORM row to a domain ``User``."""
    return User(
        id=orm.id,
        telegram_id=orm.telegram_id,
        username=orm.username,
        first_name=orm.first_name,
        last_name=orm.last_name,
        language_code=orm.language_code,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def user_to_orm(domain: User) -> UserORM:
    """Convert a domain ``User`` to an ORM instance (detached, not in session)."""
    orm = UserORM(
        telegram_id=domain.telegram_id,
        username=domain.username,
        first_name=domain.first_name,
        last_name=domain.last_name,
        language_code=domain.language_code,
        is_active=domain.is_active,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )
    if domain.id is not None:
        orm.id = domain.id
    return orm
