"""Mini App bootstrap API routes.

Provides the current-user / bootstrap endpoint that the Mini App shell
calls on startup to identify the user and discover available features.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps.auth import get_current_user
from app.api.schemas.user import AvailableFeatures, BootstrapResponse, UserResponse
from app.core.config import Settings, get_settings
from app.domain.user import User

router = APIRouter(tags=["miniapp"])


def _build_user_response(user: User) -> UserResponse:
    """Convert a domain User to a UserResponse schema."""
    return UserResponse(
        id=user.id,  # type: ignore[arg-type]
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _build_features(settings: Settings) -> AvailableFeatures:
    """Determine which optional features are available from settings."""
    has_openai = bool(settings.openai_api_key.get_secret_value())
    return AvailableFeatures(
        text_generation=has_openai,
        image_generation=has_openai,
    )


@router.get(
    "/me",
    response_model=BootstrapResponse,
    summary="Get current user and bootstrap info",
)
async def get_me(
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> BootstrapResponse:
    """Return the authenticated user's identity and available features.

    This is the first endpoint the Mini App calls on startup to identify
    the current user and configure the app shell.
    """
    return BootstrapResponse(
        user=_build_user_response(user),
        features=_build_features(settings),
    )
