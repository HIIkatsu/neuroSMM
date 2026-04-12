"""Tests for draft API endpoints."""

from __future__ import annotations

from httpx import AsyncClient

from app.domain.user import User


async def _create_project(
    client: AsyncClient, headers: dict[str, str], title: str = "Test Project"
) -> int:
    """Helper: create a project and return its ID."""
    resp = await client.post(
        "/api/v1/projects", headers=headers, json={"title": title}
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestCreateDraft:
    """Tests for POST /api/v1/projects/{project_id}/drafts."""

    async def test_create_draft_success(
        self, client: AsyncClient, auth_headers: dict[str, str], seed_user: User
    ) -> None:
        project_id = await _create_project(client, auth_headers)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "My Draft", "text_content": "Hello world"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Draft"
        assert data["text_content"] == "Hello world"
        assert data["project_id"] == project_id
        assert data["author_id"] == seed_user.id
        assert data["status"] == "draft"
        assert "id" in data

    async def test_create_draft_minimal(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "draft"

    async def test_create_draft_in_other_users_project_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        project_id = await _create_project(client, auth_headers)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers_b,
            json={"title": "Intruder"},
        )
        assert resp.status_code == 403

    async def test_create_draft_nonexistent_project_returns_404(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/projects/99999/drafts",
            headers=auth_headers,
            json={"title": "Ghost"},
        )
        assert resp.status_code == 404


class TestListDrafts:
    """Tests for GET /api/v1/projects/{project_id}/drafts."""

    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["count"] == 0

    async def test_list_drafts_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)

        await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "Draft 1"},
        )
        await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "Draft 2"},
        )

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

    async def test_list_drafts_other_users_project_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        project_id = await _create_project(client, auth_headers)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts", headers=auth_headers_b
        )
        assert resp.status_code == 403


class TestGetDraft:
    """Tests for GET /api/v1/projects/{project_id}/drafts/{draft_id}."""

    async def test_get_draft_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "Get Me"},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Me"

    async def test_get_draft_other_user_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "Secret"},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}",
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    async def test_get_nonexistent_draft_returns_404(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/99999",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestUpdateDraft:
    """Tests for PATCH /api/v1/projects/{project_id}/drafts/{draft_id}."""

    async def test_update_title(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "Old"},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}",
            headers=auth_headers,
            json={"title": "New"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    async def test_update_text_content(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"text_content": "original"},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}",
            headers=auth_headers,
            json={"text_content": "updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["text_content"] == "updated"

    async def test_update_other_users_draft_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "Protected"},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}",
            headers=auth_headers_b,
            json={"title": "Hijacked"},
        )
        assert resp.status_code == 403


class TestDraftStateTransitions:
    """Tests for draft state transition endpoints."""

    async def test_mark_ready(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "Ready Draft", "text_content": "Some content"},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/ready",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    async def test_mark_ready_without_content_fails(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/ready",
            headers=auth_headers,
        )
        # ValidationError from domain → 422
        assert resp.status_code == 422

    async def test_send_back_to_draft(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"text_content": "Content"},
        )
        draft_id = create_resp.json()["id"]

        # Mark ready first
        await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/ready",
            headers=auth_headers,
        )

        # Send back to draft
        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/back-to-draft",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "draft"

    async def test_archive_draft(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "To Archive"},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/archive",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    async def test_archive_already_archived_fails(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"title": "Already Archived"},
        )
        draft_id = create_resp.json()["id"]

        # Archive
        await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/archive",
            headers=auth_headers,
        )

        # Try to archive again
        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/archive",
            headers=auth_headers,
        )
        # ConflictError → 409
        assert resp.status_code == 409

    async def test_state_transition_other_user_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts",
            headers=auth_headers,
            json={"text_content": "Content"},
        )
        draft_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/ready",
            headers=auth_headers_b,
        )
        assert resp.status_code == 403
