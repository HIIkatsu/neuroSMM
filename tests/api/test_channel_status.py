"""Tests for channel status endpoint.

Covers GET /api/v1/projects/{pid}/channel/status for bound/unbound
projects, ownership enforcement, and missing resources.
"""

from __future__ import annotations

from httpx import AsyncClient


async def _create_project(
    client: AsyncClient, headers: dict[str, str], title: str = "Test Project"
) -> int:
    """Helper: create a project and return its ID."""
    resp = await client.post(
        "/api/v1/projects", headers=headers, json={"title": title}
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestChannelStatus:
    """Tests for GET /api/v1/projects/{pid}/channel/status."""

    async def test_unbound_project_returns_not_bound(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """A fresh project without a bound channel reports is_bound=False."""
        project_id = await _create_project(client, auth_headers)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/channel/status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == project_id
        assert data["is_bound"] is False
        assert data["channel_id"] is None

    async def test_bound_project_returns_channel_id(
        self, client: AsyncClient, auth_headers: dict[str, str], session_factory
    ) -> None:
        """A project with a bound channel reports is_bound=True and the channel_id."""
        project_id = await _create_project(client, auth_headers)

        # Directly bind a channel via the DB to avoid needing Telegram API
        from app.integrations.db.repositories.project import ProjectRepository

        async with session_factory() as session:
            repo = ProjectRepository(session)
            project = await repo.get_by_id(project_id)
            linked = project.link_channel("-1001234567890")
            await repo.update(linked)
            await session.commit()

        resp = await client.get(
            f"/api/v1/projects/{project_id}/channel/status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == project_id
        assert data["is_bound"] is True
        assert data["channel_id"] == "-1001234567890"

    async def test_ownership_enforced(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        """Channel status check is denied for a project the user doesn't own."""
        project_id = await _create_project(client, auth_headers)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/channel/status",
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    async def test_nonexistent_project_returns_404(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Channel status on a missing project returns 404."""
        resp = await client.get(
            "/api/v1/projects/99999/channel/status",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_missing_auth_returns_401(self, client: AsyncClient) -> None:
        """Channel status without auth returns 401."""
        resp = await client.get("/api/v1/projects/1/channel/status")
        assert resp.status_code == 401

    async def test_response_shape(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Response has exactly the expected keys."""
        project_id = await _create_project(client, auth_headers)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/channel/status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        expected_keys = {"project_id", "is_bound", "channel_id"}
        assert set(resp.json().keys()) == expected_keys
