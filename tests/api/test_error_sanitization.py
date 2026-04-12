"""Tests for error sanitization — internal details must never leak to clients.

Verifies that:
- ExternalServiceError messages are replaced with safe generic messages
- Unhandled exceptions produce a generic 500 response
- Domain validation / authorization errors retain their messages
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.error_handlers import register_exception_handlers
from app.core.exceptions import (
    AuthorizationError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)


def _build_app() -> FastAPI:
    """Build a minimal app with error handlers and test routes."""
    app = FastAPI(debug=False)
    register_exception_handlers(app)

    @app.get("/external")
    async def raise_external():
        raise ExternalServiceError(
            "Incorrect API key provided: sk-proj-abc123... "
            "You can find your API key at https://platform.openai.com"
        )

    @app.get("/validation")
    async def raise_validation():
        raise ValidationError("Поле 'title' обязательно")

    @app.get("/authorization")
    async def raise_authorization():
        raise AuthorizationError("У вас нет доступа к этому проекту")

    @app.get("/not-found")
    async def raise_not_found():
        raise NotFoundError("Черновик не найден")

    @app.get("/unhandled")
    async def raise_unhandled():
        raise RuntimeError("Unexpected database connection pool exhausted")

    return app


@pytest.fixture()
async def test_client():
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestErrorSanitization:
    """Error response sanitization tests."""

    async def test_external_service_error_sanitized(
        self, test_client: AsyncClient
    ) -> None:
        """ExternalServiceError must NOT leak raw provider message."""
        resp = await test_client.get("/external")
        body = resp.json()
        detail = body["detail"]

        # Must NOT contain API key or platform URL
        assert "sk-proj" not in detail
        assert "openai.com" not in detail
        assert "API key" not in detail

        # Must be a safe generic message
        assert "Внешний сервис" in detail or "недоступен" in detail

    async def test_validation_error_preserves_message(
        self, test_client: AsyncClient
    ) -> None:
        """ValidationError messages should pass through (they're safe)."""
        resp = await test_client.get("/validation")
        assert resp.status_code == 422
        assert "title" in resp.json()["detail"]

    async def test_authorization_error_preserves_message(
        self, test_client: AsyncClient
    ) -> None:
        """AuthorizationError messages should pass through."""
        resp = await test_client.get("/authorization")
        assert resp.status_code == 403
        assert "доступа" in resp.json()["detail"]

    async def test_not_found_error_preserves_message(
        self, test_client: AsyncClient
    ) -> None:
        """NotFoundError messages should pass through."""
        resp = await test_client.get("/not-found")
        assert resp.status_code == 404
        assert "не найден" in resp.json()["detail"]

    async def test_unhandled_exception_returns_generic_500(
        self, test_client: AsyncClient
    ) -> None:
        """Unhandled exceptions must return generic 500 — no internals."""
        resp = await test_client.get("/unhandled")
        assert resp.status_code == 500
        detail = resp.json()["detail"]

        # Must NOT leak the internal error message
        assert "database" not in detail.lower()
        assert "connection pool" not in detail.lower()
        assert "RuntimeError" not in detail

        # Must be a safe generic message
        assert "ошибка" in detail.lower() or "сервер" in detail.lower()
