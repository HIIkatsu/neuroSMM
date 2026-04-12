"""
User repository — async SQLAlchemy implementation.

Returns domain :class:`User` objects; ORM types never leak to callers.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.user import User
from app.integrations.db.mappers.user import user_to_domain, user_to_orm
from app.integrations.db.models.user import UserORM


class UserRepository:
    """Async repository for :class:`User` persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        """Insert a new user and return the domain model with an assigned ID."""
        orm = user_to_orm(user)
        self._session.add(orm)
        await self._session.flush()
        return user_to_domain(orm)

    async def get_by_id(self, user_id: int) -> User:
        """Load a user by its surrogate ID.

        Raises :class:`NotFoundError` if no such user exists.
        """
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise NotFoundError(f"User with id={user_id} not found")
        return user_to_domain(orm)

    async def get_by_telegram_id(self, telegram_id: int) -> User:
        """Load a user by Telegram user ID.

        Raises :class:`NotFoundError` if no such user exists.
        """
        stmt = select(UserORM).where(UserORM.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise NotFoundError(f"User with telegram_id={telegram_id} not found")
        return user_to_domain(orm)

    async def update(self, user: User) -> User:
        """Persist an updated domain user, merging changes into the session.

        Raises :class:`NotFoundError` if the user's ID doesn't exist in the DB.
        """
        if user.id is None:
            raise NotFoundError("Cannot update a user without an ID")

        stmt = select(UserORM).where(UserORM.id == user.id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            raise NotFoundError(f"User with id={user.id} not found")

        existing.telegram_id = user.telegram_id
        existing.username = user.username
        existing.first_name = user.first_name
        existing.last_name = user.last_name
        existing.language_code = user.language_code
        existing.is_active = user.is_active
        existing.created_at = user.created_at
        existing.updated_at = user.updated_at

        await self._session.flush()
        return user_to_domain(existing)

    async def list_active(self) -> list[User]:
        """Return all active users."""
        stmt = select(UserORM).where(UserORM.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [user_to_domain(orm) for orm in result.scalars().all()]
