"""Tests for project API endpoints."""

from __future__ import annotations

from httpx import AsyncClient

from app.domain.user import User


class TestCreateProject:
    """Tests for POST /api/v1/projects."""

    async def test_create_project_success(
        self, client: AsyncClient, auth_headers: dict[str, str], seed_user: User
    ) -> None:
        resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "My Channel", "description": "A test channel"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Channel"
        assert data["description"] == "A test channel"
        assert data["owner_id"] == seed_user.id
        assert data["is_active"] is True
        assert data["platform"] == "telegram"
        assert "id" in data
        assert "created_at" in data

    async def test_create_project_minimal(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "Minimal"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Minimal"
        assert data["description"] == ""

    async def test_create_project_empty_title_fails(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": ""},
        )
        assert resp.status_code == 422

    async def test_create_project_no_auth_fails(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/projects",
            json={"title": "No Auth"},
        )
        assert resp.status_code == 401


class TestListProjects:
    """Tests for GET /api/v1/projects."""

    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/projects", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["count"] == 0

    async def test_list_returns_only_own_projects(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        # Create projects for user A
        await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "User A Project"},
        )
        # Create projects for user B
        await client.post(
            "/api/v1/projects",
            headers=auth_headers_b,
            json={"title": "User B Project"},
        )

        # User A sees only their project
        resp = await client.get("/api/v1/projects", headers=auth_headers)
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["title"] == "User A Project"

        # User B sees only their project
        resp = await client.get("/api/v1/projects", headers=auth_headers_b)
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["title"] == "User B Project"


class TestGetProject:
    """Tests for GET /api/v1/projects/{project_id}."""

    async def test_get_own_project(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "Get Me"},
        )
        project_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/projects/{project_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Me"

    async def test_get_other_users_project_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        create_resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "Private"},
        )
        project_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/projects/{project_id}", headers=auth_headers_b
        )
        assert resp.status_code == 403

    async def test_get_nonexistent_project_returns_404(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/projects/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateProject:
    """Tests for PATCH /api/v1/projects/{project_id}."""

    async def test_update_title(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "Old Title"},
        )
        project_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
            json={"title": "New Title"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    async def test_update_description(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "With Desc"},
        )
        project_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
            json={"description": "Updated description"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    async def test_update_other_users_project_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        create_resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "Mine"},
        )
        project_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers_b,
            json={"title": "Hijacked"},
        )
        assert resp.status_code == 403


class TestDeactivateActivateProject:
    """Tests for project deactivation/activation endpoints."""

    async def test_deactivate_project(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "Active"},
        )
        project_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/projects/{project_id}/deactivate", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_activate_project(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "To Reactivate"},
        )
        project_id = create_resp.json()["id"]

        # Deactivate first
        await client.post(
            f"/api/v1/projects/{project_id}/deactivate", headers=auth_headers
        )

        # Activate
        resp = await client.post(
            f"/api/v1/projects/{project_id}/activate", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    async def test_deactivate_other_users_project_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        create_resp = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"title": "Protected"},
        )
        project_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/projects/{project_id}/deactivate",
            headers=auth_headers_b,
        )
        assert resp.status_code == 403
