"""Tests for preview and publish API endpoints."""

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


async def _create_draft(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: int,
    *,
    title: str = "My Draft",
    text_content: str = "Hello world",
) -> int:
    """Helper: create a draft and return its ID."""
    resp = await client.post(
        f"/api/v1/projects/{project_id}/drafts",
        headers=headers,
        json={"title": title, "text_content": text_content},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _mark_ready(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: int,
    draft_id: int,
) -> None:
    """Helper: mark a draft as ready."""
    resp = await client.post(
        f"/api/v1/projects/{project_id}/drafts/{draft_id}/ready",
        headers=headers,
    )
    assert resp.status_code == 200


class TestPreview:
    """Tests for GET /api/v1/projects/{pid}/drafts/{did}/preview."""

    async def test_preview_draft_status(
        self, client: AsyncClient, auth_headers: dict[str, str], seed_user: User
    ) -> None:
        """Preview succeeds for a draft in DRAFT status."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["draft_id"] == draft_id
        assert data["project_id"] == project_id
        assert data["title"] == "My Draft"
        assert data["text_content"] == "Hello world"
        assert data["status"] == "draft"

    async def test_preview_ready_status(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Preview succeeds for a draft in READY status."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)
        await _mark_ready(client, auth_headers, project_id, draft_id)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    async def test_preview_includes_all_fields(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Preview response includes all expected fields."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/preview",
            headers=auth_headers,
        )
        data = resp.json()
        assert "draft_id" in data
        assert "project_id" in data
        assert "title" in data
        assert "text_content" in data
        assert "image_url" in data
        assert "content_type" in data
        assert "tone" in data
        assert "status" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_preview_ownership_enforced(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        """Preview is denied when user does not own the project."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/preview",
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    async def test_preview_nonexistent_draft_returns_404(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Preview returns 404 for a non-existent draft."""
        project_id = await _create_project(client, auth_headers)

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/99999/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_preview_archived_draft_rejected(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Preview is denied for an archived draft."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        # Archive the draft
        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/archive",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestPublish:
    """Tests for POST /api/v1/projects/{pid}/drafts/{did}/publish."""

    async def test_successful_publish(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Publish succeeds for a READY draft."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)
        await _mark_ready(client, auth_headers, project_id, draft_id)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/publish",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["draft_id"] == draft_id
        assert data["status"] == "published"
        assert data["published"] is True

    async def test_publish_updates_draft_state(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """After publish, the draft status is PUBLISHED when fetched."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)
        await _mark_ready(client, auth_headers, project_id, draft_id)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/publish",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Verify via GET
        get_resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}",
            headers=auth_headers,
        )
        assert get_resp.json()["status"] == "published"

    async def test_publish_draft_status_not_ready_rejected(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Publish fails for a draft still in DRAFT status."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/publish",
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_publish_ownership_enforced(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        """Publish is denied when user does not own the project."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)
        await _mark_ready(client, auth_headers, project_id, draft_id)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/publish",
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    async def test_publish_already_published_rejected(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Cannot publish a draft that is already published."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)
        await _mark_ready(client, auth_headers, project_id, draft_id)

        # First publish
        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/publish",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Second publish attempt
        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/publish",
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_publish_archived_draft_rejected(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Publish fails for an archived draft."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        # Archive
        await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/archive",
            headers=auth_headers,
        )

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/publish",
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_publish_nonexistent_draft_returns_404(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Publish returns 404 for a non-existent draft."""
        project_id = await _create_project(client, auth_headers)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/99999/publish",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_publish_response_correctness(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Publish response includes all expected fields."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)
        await _mark_ready(client, auth_headers, project_id, draft_id)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/publish",
            headers=auth_headers,
        )
        data = resp.json()
        assert "draft_id" in data
        assert "status" in data
        assert "platform_post_id" in data
        assert "published" in data
