"""Shared fixtures for bot unit tests."""

from __future__ import annotations

import pytest

from app.core.config import Environment, Settings


@pytest.fixture()
def settings_with_miniapp() -> Settings:
    """Settings with a valid Mini App URL and a dummy bot token."""
    return Settings(
        environment=Environment.TESTING,
        bot_token="1234567890:AABBCCDDEEFFaabbccddeeff1234567890AB",  # type: ignore[arg-type]
        miniapp_url="https://t.me/neurosmm_bot/app",
    )


@pytest.fixture()
def settings_no_miniapp() -> Settings:
    """Settings without a Mini App URL configured."""
    return Settings(
        environment=Environment.TESTING,
        bot_token="1234567890:AABBCCDDEEFFaabbccddeeff1234567890AB",  # type: ignore[arg-type]
    )
