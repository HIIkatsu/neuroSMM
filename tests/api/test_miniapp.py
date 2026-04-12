"""Tests for Mini App bootstrap / current-user endpoint.

Covers the /me endpoint and the bootstrap response shape including
authentication, user data correctness, and feature flags.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.domain.user import User


class TestBootstrapEndpoint:
    """Tests for GET /api/v1/me."""

    async def test_authenticated_user_returns_bootstrap(
        self, client: AsyncClient, auth_headers: dict[str, str], seed_user: User
    ) -> None:
        """Valid auth returns 200 with user data and feature flags."""
        resp = await client.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        # Top-level shape
        assert "user" in data
        assert "features" in data

        # User fields
        user_data = data["user"]
        assert user_data["id"] == seed_user.id
        assert user_data["telegram_id"] == seed_user.telegram_id
        assert user_data["username"] == seed_user.username
        assert user_data["first_name"] == seed_user.first_name
        assert user_data["is_active"] is True
        assert "created_at" in user_data
        assert "updated_at" in user_data

    async def test_bootstrap_returns_feature_flags(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Bootstrap response includes feature availability flags."""
        resp = await client.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        features = resp.json()["features"]
        assert "text_generation" in features
        assert "image_generation" in features
        # In test config, no OpenAI key → features should be False
        assert features["text_generation"] is False
        assert features["image_generation"] is False

    async def test_missing_auth_returns_401(self, client: AsyncClient) -> None:
        """Request without auth headers returns 401."""
        resp = await client.get("/api/v1/me")
        assert resp.status_code == 401
        assert "detail" in resp.json()

    async def test_nonexistent_user_returns_401(self, client: AsyncClient) -> None:
        """Request with a non-existent user ID returns 401."""
        resp = await client.get(
            "/api/v1/me", headers={"X-Dev-User-Id": "99999"}
        )
        assert resp.status_code == 401

    async def test_deactivated_user_returns_401(
        self, client: AsyncClient, session_factory
    ) -> None:
        """Deactivated user gets 401 on bootstrap."""
        from app.integrations.db.repositories.user import UserRepository

        async with session_factory() as session:
            repo = UserRepository(session)
            user = await repo.create(
                User(telegram_id=888888, username="inactive", first_name="Inactive")
            )
            deactivated = user.deactivate()
            await repo.update(deactivated)
            await session.commit()
            user_id = user.id

        resp = await client.get(
            "/api/v1/me", headers={"X-Dev-User-Id": str(user_id)}
        )
        assert resp.status_code == 401

    async def test_user_response_has_all_fields(
        self, client: AsyncClient, auth_headers: dict[str, str], seed_user: User
    ) -> None:
        """All expected user fields are present in the response."""
        resp = await client.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        user_data = resp.json()["user"]
        expected_keys = {
            "id", "telegram_id", "username", "first_name", "last_name",
            "language_code", "is_active", "created_at", "updated_at",
        }
        assert expected_keys == set(user_data.keys())

    async def test_second_user_gets_own_data(
        self,
        client: AsyncClient,
        auth_headers_b: dict[str, str],
        seed_user_b: User,
    ) -> None:
        """Each authenticated user receives their own data."""
        resp = await client.get("/api/v1/me", headers=auth_headers_b)
        assert resp.status_code == 200
        user_data = resp.json()["user"]
        assert user_data["id"] == seed_user_b.id
        assert user_data["telegram_id"] == seed_user_b.telegram_id
        assert user_data["username"] == seed_user_b.username
