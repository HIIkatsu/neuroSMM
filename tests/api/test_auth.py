"""Tests for temporary dev auth dependency."""

from __future__ import annotations

from httpx import AsyncClient

from app.domain.user import User


class TestDevAuth:
    """Tests for the X-Dev-User-Id temporary auth mechanism."""

    async def test_missing_header_returns_401(self, client: AsyncClient) -> None:
        """Requests without the auth header should get 401."""
        resp = await client.get("/api/v1/projects")
        assert resp.status_code == 401
        assert "Missing" in resp.json()["detail"]

    async def test_nonexistent_user_returns_401(self, client: AsyncClient) -> None:
        """Requests with a non-existent user ID should get 401."""
        resp = await client.get(
            "/api/v1/projects", headers={"X-Dev-User-Id": "99999"}
        )
        assert resp.status_code == 401

    async def test_valid_user_succeeds(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Requests with a valid user ID should succeed."""
        resp = await client.get("/api/v1/projects", headers=auth_headers)
        assert resp.status_code == 200

    async def test_deactivated_user_returns_401(
        self,
        client: AsyncClient,
        session_factory,
    ) -> None:
        """Deactivated users should get 401."""
        from app.integrations.db.repositories.user import UserRepository

        async with session_factory() as session:
            repo = UserRepository(session)
            user = await repo.create(
                User(telegram_id=999999, username="deactivated", first_name="Deact")
            )
            deactivated = user.deactivate()
            await repo.update(deactivated)
            await session.commit()
            user_id = user.id

        resp = await client.get(
            "/api/v1/projects", headers={"X-Dev-User-Id": str(user_id)}
        )
        assert resp.status_code == 401
