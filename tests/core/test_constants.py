"""Tests for app.core.constants."""

from __future__ import annotations

from app.core.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_API_PREFIX,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)


class TestConstants:
    """Shared constants must have expected values."""

    def test_app_name(self) -> None:
        assert APP_NAME == "NeuroSMM"

    def test_app_version_is_v2_dev(self) -> None:
        assert APP_VERSION.startswith("2.")

    def test_default_api_prefix(self) -> None:
        assert DEFAULT_API_PREFIX.startswith("/api/")

    def test_page_size_limits_sane(self) -> None:
        assert 0 < DEFAULT_PAGE_SIZE <= MAX_PAGE_SIZE
