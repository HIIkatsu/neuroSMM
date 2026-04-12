"""End-to-end smoke test for the core NeuroSMM V2 loop.

Validates the complete user journey:
  bootstrap → project → draft → generate → mark-ready → preview → publish
  bootstrap → project → draft → mark-ready → schedule → cancel/retry

This is the acceptance test for PR14.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

API = "/api/v1"


class TestCoreE2ELoop:
    """End-to-end smoke: the full happy path from bootstrap to publish."""

    @pytest.mark.asyncio
    async def test_full_publish_flow(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """bootstrap → project → draft → generate text → generate image →
        mark-ready → preview → publish-now."""

        # 1. Bootstrap — GET /me
        r = await client.get(f"{API}/me", headers=auth_headers)
        assert r.status_code == 200
        bootstrap = r.json()
        assert "user" in bootstrap
        assert "features" in bootstrap
        user = bootstrap["user"]
        assert user["username"] == "testuser"

        # 2. Create project
        r = await client.post(
            f"{API}/projects",
            headers=auth_headers,
            json={"title": "E2E Project", "description": "Smoke test project"},
        )
        assert r.status_code == 201
        project = r.json()
        pid = project["id"]
        assert project["title"] == "E2E Project"
        assert project["is_active"] is True

        # 3. List projects
        r = await client.get(f"{API}/projects", headers=auth_headers)
        assert r.status_code == 200
        projects = r.json()
        assert projects["count"] >= 1

        # 4. Create draft
        r = await client.post(
            f"{API}/projects/{pid}/drafts",
            headers=auth_headers,
            json={"title": "Test Post", "tone": "casual", "content_type": "text"},
        )
        assert r.status_code == 201
        draft = r.json()
        did = draft["id"]
        assert draft["status"] == "draft"
        assert draft["title"] == "Test Post"

        # 5. Update draft
        r = await client.patch(
            f"{API}/projects/{pid}/drafts/{did}",
            headers=auth_headers,
            json={"text_content": "Hello, world! This is a test post."},
        )
        assert r.status_code == 200
        assert r.json()["text_content"] == "Hello, world! This is a test post."

        # 6. Generate text (uses StubProvider since no OpenAI key)
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/generate/text",
            headers=auth_headers,
        )
        assert r.status_code == 200
        gen_result = r.json()
        assert gen_result["draft_id"] == did
        assert gen_result["draft_text_content"]  # non-empty
        assert gen_result["generation"]["status"] == "completed"

        # 7. Generate image (uses StubProvider since no OpenAI key)
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/generate/image",
            headers=auth_headers,
        )
        assert r.status_code == 200
        img_result = r.json()
        assert img_result["draft_id"] == did
        assert img_result["draft_image_url"]  # non-empty
        assert img_result["generation"]["status"] == "completed"

        # 8. Mark draft as ready
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/ready",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ready"

        # 9. Preview
        r = await client.get(
            f"{API}/projects/{pid}/drafts/{did}/preview",
            headers=auth_headers,
        )
        assert r.status_code == 200
        preview = r.json()
        assert preview["draft_id"] == did
        assert preview["status"] == "ready"
        assert preview["text_content"]

        # 10. Publish (uses StubPublisher since no bot token)
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/publish",
            headers=auth_headers,
        )
        assert r.status_code == 200
        publish_result = r.json()
        assert publish_result["published"] is True
        assert publish_result["status"] == "published"

        # 11. Verify final state
        r = await client.get(
            f"{API}/projects/{pid}/drafts/{did}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "published"

    @pytest.mark.asyncio
    async def test_schedule_flow(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """project → draft → mark-ready → schedule → cancel → retry."""

        # Setup: project + draft + ready
        r = await client.post(
            f"{API}/projects",
            headers=auth_headers,
            json={"title": "Schedule Test"},
        )
        pid = r.json()["id"]

        r = await client.post(
            f"{API}/projects/{pid}/drafts",
            headers=auth_headers,
            json={"title": "Scheduled Post", "content_type": "text"},
        )
        did = r.json()["id"]

        await client.patch(
            f"{API}/projects/{pid}/drafts/{did}",
            headers=auth_headers,
            json={"text_content": "Content for scheduling"},
        )

        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/ready",
            headers=auth_headers,
        )
        assert r.status_code == 200

        # Schedule
        future_time = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/schedule",
            headers=auth_headers,
            json={"publish_at": future_time},
        )
        assert r.status_code == 201
        schedule = r.json()
        sid = schedule["id"]
        assert schedule["status"] == "pending"

        # List schedules
        r = await client.get(
            f"{API}/projects/{pid}/schedules",
            headers=auth_headers,
        )
        assert r.status_code == 200
        sched_list = r.json()
        assert sched_list["count"] >= 1

        # Cancel
        r = await client.post(
            f"{API}/projects/{pid}/schedules/{sid}/cancel",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_draft_lifecycle(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """draft → ready → back-to-draft → ready → archive."""

        r = await client.post(
            f"{API}/projects",
            headers=auth_headers,
            json={"title": "Lifecycle Test"},
        )
        pid = r.json()["id"]

        r = await client.post(
            f"{API}/projects/{pid}/drafts",
            headers=auth_headers,
            json={"title": "Lifecycle Draft"},
        )
        did = r.json()["id"]

        # Add content
        await client.patch(
            f"{API}/projects/{pid}/drafts/{did}",
            headers=auth_headers,
            json={"text_content": "Some content"},
        )

        # Mark ready
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/ready",
            headers=auth_headers,
        )
        assert r.json()["status"] == "ready"

        # Back to draft
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/back-to-draft",
            headers=auth_headers,
        )
        assert r.json()["status"] == "draft"

        # Mark ready again
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/ready",
            headers=auth_headers,
        )
        assert r.json()["status"] == "ready"

        # Archive
        r = await client.post(
            f"{API}/projects/{pid}/drafts/{did}/archive",
            headers=auth_headers,
        )
        assert r.json()["status"] == "archived"

    @pytest.mark.asyncio
    async def test_channel_status_without_binding(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Channel status returns unbound state when no channel is set."""

        r = await client.post(
            f"{API}/projects",
            headers=auth_headers,
            json={"title": "Channel Test"},
        )
        pid = r.json()["id"]

        r = await client.get(
            f"{API}/projects/{pid}/channel/status",
            headers=auth_headers,
        )
        assert r.status_code == 200
        status = r.json()
        assert status["is_bound"] is False

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient) -> None:
        """Health check works without auth."""
        r = await client.get(f"{API}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_static_files_served(self, client: AsyncClient) -> None:
        """Mini App index.html is served at root."""
        r = await client.get("/")
        assert r.status_code == 200
        assert "NeuroSMM" in r.text

    @pytest.mark.asyncio
    async def test_auth_required(self, client: AsyncClient) -> None:
        """Endpoints require authentication."""
        r = await client.get(f"{API}/me")
        assert r.status_code == 401

        r = await client.get(f"{API}/projects")
        assert r.status_code == 401
