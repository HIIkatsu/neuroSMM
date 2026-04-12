"""Tests for the image generation API endpoint."""

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
    title: str = "Test Draft",
    topic: str = "AI trends",
    tone: str = "neutral",
    text_content: str = "",
) -> int:
    """Helper: create a draft and return its ID."""
    resp = await client.post(
        f"/api/v1/projects/{project_id}/drafts",
        headers=headers,
        json={
            "title": title,
            "topic": topic,
            "tone": tone,
            "text_content": text_content,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestGenerateImage:
    """Tests for POST /api/v1/projects/{pid}/drafts/{did}/generate/image."""

    async def test_generate_image_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        seed_user: User,
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(
            client, auth_headers, project_id, topic="AI trends", tone="casual"
        )

        # No OpenAI key configured → StubImageProvider is used automatically
        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/generate/image",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["draft_id"] == draft_id
        assert data["draft_image_url"]  # non-empty
        assert data["generation"]["status"] == "completed"
        assert data["generation"]["generation_type"] == "image"
        assert data["generation"]["content"]  # non-empty

    async def test_generate_image_updates_draft(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        seed_user: User,
    ) -> None:
        """Verify the draft's image_url is updated after generation."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/generate/image",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Fetch the draft and confirm image_url was set
        get_resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["image_url"] is not None
        assert get_resp.json()["image_url"] != ""

    async def test_generate_image_other_user_returns_403(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_b: dict[str, str],
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/generate/image",
            headers=auth_headers_b,
        )
        assert resp.status_code == 403

    async def test_generate_image_nonexistent_draft_returns_404(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        project_id = await _create_project(client, auth_headers)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/99999/generate/image",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_generate_image_archived_draft_returns_422(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        # Archive the draft
        await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/archive",
            headers=auth_headers,
        )

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/generate/image",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_generate_image_no_auth_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/v1/projects/1/drafts/1/generate/image",
        )
        assert resp.status_code == 401

    async def test_generate_image_response_has_generation_metadata(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        seed_user: User,
    ) -> None:
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/generate/image",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        gen = resp.json()["generation"]
        assert "model_name" in gen
        assert "prompt_used" in gen
        assert "created_at" in gen

    async def test_generate_image_then_text_both_persist(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        seed_user: User,
    ) -> None:
        """Generating both image and text should persist both fields on the draft."""
        project_id = await _create_project(client, auth_headers)
        draft_id = await _create_draft(client, auth_headers, project_id)

        # Generate image first
        img_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/generate/image",
            headers=auth_headers,
        )
        assert img_resp.status_code == 200

        # Generate text second
        txt_resp = await client.post(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}/generate/text",
            headers=auth_headers,
        )
        assert txt_resp.status_code == 200

        # Fetch the draft and verify both fields are set
        get_resp = await client.get(
            f"/api/v1/projects/{project_id}/drafts/{draft_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 200
        draft_data = get_resp.json()
        assert draft_data["image_url"] is not None
        assert draft_data["text_content"] != ""
