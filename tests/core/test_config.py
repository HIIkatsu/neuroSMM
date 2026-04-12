"""Tests for app.core.config — settings loading and validation."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.core.config import Environment, LogLevel, Settings, _get_settings_cached, get_settings


class TestSettingsDefaults:
    """Settings should have sensible defaults when no env vars are set."""

    def test_default_environment(self) -> None:
        s = Settings()
        assert s.environment == Environment.DEVELOPMENT

    def test_default_log_level(self) -> None:
        s = Settings()
        assert s.log_level == LogLevel.INFO

    def test_default_debug(self) -> None:
        s = Settings()
        assert s.debug is False

    def test_default_api_port(self) -> None:
        s = Settings()
        assert s.api_port == 8000

    def test_default_api_prefix(self) -> None:
        s = Settings()
        assert s.api_prefix == "/api/v1"

    def test_default_cors_origins(self) -> None:
        s = Settings()
        assert s.cors_origins == ["*"]

    def test_default_log_json(self) -> None:
        s = Settings()
        assert s.log_json is True


class TestSettingsFromEnv:
    """Settings should be loadable from environment variables."""

    def test_environment_from_env(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            s = Settings()
        assert s.environment == Environment.PRODUCTION

    def test_log_level_from_env_case_insensitive(self) -> None:
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            s = Settings()
        assert s.log_level == LogLevel.DEBUG

    def test_debug_from_env(self) -> None:
        with patch.dict(os.environ, {"DEBUG": "true"}):
            s = Settings()
        assert s.debug is True

    def test_bot_token_is_secret(self) -> None:
        with patch.dict(os.environ, {"BOT_TOKEN": "123:ABC"}):
            s = Settings()
        assert s.bot_token.get_secret_value() == "123:ABC"
        # SecretStr must not leak the value in repr/str
        assert "123:ABC" not in repr(s.bot_token)
        assert "123:ABC" not in str(s.bot_token)

    def test_openai_api_key_is_secret(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            s = Settings()
        assert s.openai_api_key.get_secret_value() == "sk-test"
        assert "sk-test" not in repr(s.openai_api_key)

    def test_api_port_from_env(self) -> None:
        with patch.dict(os.environ, {"API_PORT": "9000"}):
            s = Settings()
        assert s.api_port == 9000

    def test_environment_normalised_from_uppercase(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "STAGING"}):
            s = Settings()
        assert s.environment == Environment.STAGING

    def test_extra_env_vars_ignored(self) -> None:
        """Extra env vars that are not fields should not cause errors."""
        with patch.dict(os.environ, {"SOME_RANDOM_VAR": "hello"}):
            s = Settings()
        assert s.app_name == "NeuroSMM"


class TestSettingsValidation:
    """Invalid values should be rejected."""

    def test_invalid_environment_rejected(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "moon"}):
            with pytest.raises(Exception):  # noqa: B017
                Settings()

    def test_invalid_log_level_rejected(self) -> None:
        with patch.dict(os.environ, {"LOG_LEVEL": "VERBOSE"}):
            with pytest.raises(Exception):  # noqa: B017
                Settings()

    def test_invalid_port_rejected(self) -> None:
        with patch.dict(os.environ, {"API_PORT": "not_a_number"}):
            with pytest.raises(Exception):  # noqa: B017
                Settings()


class TestSettingsProperties:
    """Helper properties must behave correctly."""

    def test_is_production_true(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            s = Settings()
        assert s.is_production is True

    def test_is_production_false(self) -> None:
        s = Settings()
        assert s.is_production is False

    def test_is_testing_true(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            s = Settings()
        assert s.is_testing is True

    def test_is_testing_false(self) -> None:
        s = Settings()
        assert s.is_testing is False


class TestGetSettings:
    """get_settings() must return a cached singleton."""

    def test_returns_settings_instance(self) -> None:
        _get_settings_cached.cache_clear()
        s = get_settings()
        assert isinstance(s, Settings)

    def test_returns_same_instance(self) -> None:
        _get_settings_cached.cache_clear()
        a = get_settings()
        b = get_settings()
        assert a is b
