"""
Application settings — loaded from environment variables via pydantic-settings.

Usage::

    from app.core.config import get_settings

    settings = get_settings()          # cached singleton
    print(settings.bot_token)
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Allowed log-level values (case-insensitive on input)."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Central application configuration.

    All values come from the process environment (or an ``.env`` file).
    Secrets are wrapped in ``SecretStr`` so they never leak in logs/repr.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── general ────────────────────────────────────────────────────
    app_name: str = "NeuroSMM"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # ── logging ────────────────────────────────────────────────────
    log_level: LogLevel = LogLevel.INFO
    log_json: bool = True

    # ── telegram bot ───────────────────────────────────────────────
    bot_token: SecretStr = Field(default=SecretStr(""))

    # ── api ────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # ── openai ─────────────────────────────────────────────────────
    openai_api_key: SecretStr = Field(default=SecretStr(""))

    # ── database (placeholder — activated in PR 04) ────────────────
    database_url: SecretStr = Field(default=SecretStr(""))

    # ── validators ─────────────────────────────────────────────────
    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("environment", mode="before")
    @classmethod
    def _normalise_environment(cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower()
        return v

    # ── helpers ────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING


def get_settings() -> Settings:
    """Return a cached :class:`Settings` singleton.

    The instance is created on first call and reused for the lifetime of the
    process.  In tests you can override this via dependency injection or by
    patching ``app.core.config.get_settings``.
    """
    return _get_settings_cached()


@lru_cache(maxsize=1)
def _get_settings_cached() -> Settings:
    return Settings()
