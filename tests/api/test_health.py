"""Tests for the health endpoint."""

from __future__ import annotations

from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"

    async def test_health_response_shape(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/health")
        data = resp.json()
        assert "status" in data
        assert "database" in data
