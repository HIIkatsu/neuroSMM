"""Current-user provider for API requests.

Supports two authentication modes:

1. **Production** (default): Telegram Mini App init-data validation.
   The client sends the ``X-Telegram-Init-Data`` header containing the
   raw ``initData`` string from the Telegram WebApp.  The module
   validates the HMAC signature using the bot token and resolves the
   user from the DB (auto-creating on first access).

2. **Testing/Development**: ``X-Dev-User-Id`` header with a raw integer
   user ID.  **Only active when** ``ENVIRONMENT=testing``.

All auth logic is isolated in this single module.

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
from app.core.config import Environment, Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.domain.user import User
from app.integrations.db.repositories.user import UserRepository
from app.integrations.telegram.auth import InitDataValidationError, validate_init_data

# Header names
_TELEGRAM_INIT_DATA_HEADER = "X-Telegram-Init-Data"
_DEV_USER_HEADER = "X-Dev-User-Id"


async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    x_telegram_init_data: str | None = Header(
        default=None, alias=_TELEGRAM_INIT_DATA_HEADER
    ),
    x_dev_user_id: int | None = Header(default=None, alias=_DEV_USER_HEADER),
) -> User:
    """Resolve the current user from Telegram init-data or dev header.

    Raises
    ------
    AuthenticationError
        If authentication fails for any reason.
    """
    repo = UserRepository(session)

    # Dev/test auth — only active in TESTING environment
    if settings.environment == Environment.TESTING and x_dev_user_id is not None:
        return await _resolve_dev_user(repo, x_dev_user_id)

    # Production path: Telegram init-data
    if x_telegram_init_data is not None:
        return await _resolve_telegram_user(repo, x_telegram_init_data, settings)

    # No valid auth header provided
    raise AuthenticationError("Missing authentication credentials")


async def _resolve_dev_user(repo: UserRepository, user_id: int) -> User:
    """Resolve a user via the dev header (testing only)."""
    from app.core.exceptions import NotFoundError

    try:
        user = await repo.get_by_id(user_id)
    except NotFoundError:
        raise AuthenticationError(f"User with id={user_id} not found")

    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user


async def _resolve_telegram_user(
    repo: UserRepository,
    init_data: str,
    settings: Settings,
) -> User:
    """Validate Telegram init-data and resolve or create the user."""
    bot_token = settings.bot_token.get_secret_value()
    if not bot_token:
        raise AuthenticationError("Telegram bot token is not configured")

    try:
        tg_data = validate_init_data(init_data, bot_token)
    except InitDataValidationError as exc:
        raise AuthenticationError(f"Invalid Telegram authentication: {exc}")

    # Try to find existing user by telegram_id, or auto-create
    from app.core.exceptions import NotFoundError

    try:
        user = await repo.get_by_telegram_id(tg_data.user_id)
    except NotFoundError:
        # User does not exist — create a new one
        user = User(
            telegram_id=tg_data.user_id,
            first_name=tg_data.first_name,
            last_name=tg_data.last_name,
            username=tg_data.username,
            language_code=tg_data.language_code,
        )
        user = await repo.create(user)

    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user
