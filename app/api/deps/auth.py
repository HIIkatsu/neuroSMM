"""Temporary current-user provider for development and testing.

.. warning::
    This module provides a **temporary** dev/test mechanism for resolving
    the current user in API requests.  It uses a fixed ``X-Dev-User-Id``
    header to identify the user.

    **This MUST be replaced** with real Telegram auth (e.g. init-data
    validation) in a later PR.  It is intentionally isolated in a single
    file so that replacement requires changing only this module.

Usage in routers::

    from app.api.deps.auth import get_current_user

    @router.get("/me")
    async def me(user: User = Depends(get_current_user)):
        ...
"""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.database import get_db_session
from app.core.exceptions import AuthenticationError
from app.domain.user import User
from app.integrations.db.repositories.user import UserRepository

# Header name for the temporary dev user identification
_DEV_USER_HEADER = "X-Dev-User-Id"


async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    x_dev_user_id: int | None = Header(default=None, alias=_DEV_USER_HEADER),
) -> User:
    """Resolve the current user from a dev header.

    This is a **temporary** dependency.  In production, this will be
    replaced with Telegram init-data validation.

    Raises
    ------
    AuthenticationError
        If the header is missing or references a non-existent user.
    """
    if x_dev_user_id is None:
        raise AuthenticationError("Missing X-Dev-User-Id header (temporary dev auth)")

    repo = UserRepository(session)
    try:
        user = await repo.get_by_id(x_dev_user_id)
    except Exception:
        raise AuthenticationError(f"User with id={x_dev_user_id} not found")

    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user
