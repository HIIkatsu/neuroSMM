"""Unit tests for the bot configuration and wiring.

Tests verify that:
- create_dispatcher() wires start/help routers correctly
- create_bot() raises when BOT_TOKEN is absent
- miniapp_url is picked up from Settings
"""

from __future__ import annotations

import pytest

from app.bot.app import create_dispatcher
from app.core.config import Environment, Settings


class TestCreateDispatcher:
    def test_returns_dispatcher_with_routers(self, settings_with_miniapp: Settings) -> None:
        dp = create_dispatcher(settings_with_miniapp)
        router_names = [r.name for r in dp.sub_routers]
        assert "start" in router_names
        assert "help" in router_names

    def test_dispatcher_has_exactly_two_routers(self, settings_with_miniapp: Settings) -> None:
        dp = create_dispatcher(settings_with_miniapp)
        assert len(dp.sub_routers) == 2

    def test_dispatcher_without_miniapp_url(self, settings_no_miniapp: Settings) -> None:
        # Should not raise — just produces a dispatcher with fallback text
        dp = create_dispatcher(settings_no_miniapp)
        assert len(dp.sub_routers) == 2


class TestCreateBot:
    def test_create_bot_raises_without_token(self) -> None:
        settings = Settings(environment=Environment.TESTING)
        from app.bot.app import create_bot

        with pytest.raises(RuntimeError, match="BOT_TOKEN"):
            create_bot(settings)


class TestMiniAppUrlConfig:
    def test_miniapp_url_present_in_settings(self, settings_with_miniapp: Settings) -> None:
        assert settings_with_miniapp.miniapp_url == "https://t.me/neurosmm_bot/app"

    def test_miniapp_url_defaults_to_empty(self) -> None:
        settings = Settings(environment=Environment.TESTING)
        assert settings.miniapp_url == ""

    def test_miniapp_url_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MINIAPP_URL", "https://example.com/app")

        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.miniapp_url == "https://example.com/app"
