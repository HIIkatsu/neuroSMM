"""Tests for Mini App static file serving and UI assets."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.app import create_app
from app.core.config import Environment, Settings
from app.integrations.db.base import Base


@pytest.fixture()
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def session_factory(async_engine):
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture()
async def test_app(session_factory):
    settings = Settings(
        environment=Environment.TESTING,
        debug=True,
        log_json=False,
        database_url="sqlite+aiosqlite://",
    )
    return create_app(settings=settings, session_factory=session_factory)


@pytest.fixture()
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestMiniAppStatic:
    """Tests for the Mini App static file serving."""

    async def test_index_html_served_at_root(self, client: AsyncClient):
        """GET / returns the Mini App index.html."""
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "NeuroSMM" in resp.text

    async def test_index_html_contains_telegram_sdk(self, client: AsyncClient):
        """index.html loads Telegram Mini App SDK."""
        resp = await client.get("/")
        assert "telegram-web-app.js" in resp.text

    async def test_index_html_contains_bottom_nav(self, client: AsyncClient):
        """index.html contains bottom navigation element."""
        resp = await client.get("/")
        assert 'id="bottom-nav"' in resp.text

    async def test_index_html_contains_all_screens(self, client: AsyncClient):
        """index.html contains all screen containers."""
        resp = await client.get("/")
        for screen in ["home", "create", "plan", "stats", "channel", "settings"]:
            assert f'id="screen-{screen}"' in resp.text

    async def test_css_design_tokens_served(self, client: AsyncClient):
        """CSS design tokens file is accessible."""
        resp = await client.get("/static/css/design-tokens.css")
        assert resp.status_code == 200
        assert "--bg-root" in resp.text

    async def test_css_base_served(self, client: AsyncClient):
        """CSS base file is accessible."""
        resp = await client.get("/static/css/base.css")
        assert resp.status_code == 200

    async def test_css_components_served(self, client: AsyncClient):
        """CSS components file is accessible."""
        resp = await client.get("/static/css/components.css")
        assert resp.status_code == 200
        assert ".bottom-nav" in resp.text

    async def test_js_api_served(self, client: AsyncClient):
        """JS API client is accessible."""
        resp = await client.get("/static/js/api.js")
        assert resp.status_code == 200
        assert "API" in resp.text

    async def test_js_app_served(self, client: AsyncClient):
        """JS app controller is accessible."""
        resp = await client.get("/static/js/app.js")
        assert resp.status_code == 200
        assert "App" in resp.text

    async def test_js_store_served(self, client: AsyncClient):
        """JS store module is accessible."""
        resp = await client.get("/static/js/store.js")
        assert resp.status_code == 200
        assert "Store" in resp.text

    async def test_js_icons_served(self, client: AsyncClient):
        """JS icons module is accessible."""
        resp = await client.get("/static/js/icons.js")
        assert resp.status_code == 200
        assert "Icons" in resp.text

    async def test_js_onboarding_served(self, client: AsyncClient):
        """JS onboarding module is accessible."""
        resp = await client.get("/static/js/onboarding.js")
        assert resp.status_code == 200
        assert "Onboarding" in resp.text

    async def test_js_screen_home_served(self, client: AsyncClient):
        """JS home screen module is accessible."""
        resp = await client.get("/static/js/screen-home.js")
        assert resp.status_code == 200
        assert "ScreenHome" in resp.text

    async def test_js_screen_create_served(self, client: AsyncClient):
        """JS create screen module is accessible."""
        resp = await client.get("/static/js/screen-create.js")
        assert resp.status_code == 200
        assert "ScreenCreate" in resp.text

    async def test_js_screen_plan_served(self, client: AsyncClient):
        """JS plan screen module is accessible."""
        resp = await client.get("/static/js/screen-plan.js")
        assert resp.status_code == 200
        assert "ScreenPlan" in resp.text

    async def test_js_screen_stats_served(self, client: AsyncClient):
        """JS stats screen module is accessible."""
        resp = await client.get("/static/js/screen-stats.js")
        assert resp.status_code == 200
        assert "ScreenStats" in resp.text

    async def test_js_screen_channel_served(self, client: AsyncClient):
        """JS channel screen module is accessible."""
        resp = await client.get("/static/js/screen-channel.js")
        assert resp.status_code == 200
        assert "ScreenChannel" in resp.text

    async def test_js_screen_settings_served(self, client: AsyncClient):
        """JS settings screen module is accessible."""
        resp = await client.get("/static/js/screen-settings.js")
        assert resp.status_code == 200
        assert "ScreenSettings" in resp.text

    async def test_js_ui_helpers_served(self, client: AsyncClient):
        """JS UI helpers module is accessible."""
        resp = await client.get("/static/js/ui.js")
        assert resp.status_code == 200
        assert "UI" in resp.text

    async def test_api_still_works(self, client: AsyncClient):
        """API endpoints still function with static file serving enabled."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")


class TestMiniAppDesignSystem:
    """Verify the design system implements the screenshot-based visual language."""

    async def test_dark_premium_palette(self, client: AsyncClient):
        """Design tokens define the dark premium palette."""
        resp = await client.get("/static/css/design-tokens.css")
        text = resp.text
        # Dark backgrounds
        assert "--bg-root: #0d0f1a" in text
        assert "--bg-surface: #141627" in text
        assert "--bg-card: #1a1d32" in text
        # Violet accent
        assert "--accent: #8b5cf6" in text
        # Glow effects
        assert "--glow-sm" in text
        assert "--glow-md" in text

    async def test_card_heavy_composition(self, client: AsyncClient):
        """Components CSS includes card, hero-card, timeline-card styles."""
        resp = await client.get("/static/css/components.css")
        text = resp.text
        assert ".card" in text
        assert ".hero-card" in text
        assert ".timeline-card" in text
        assert ".timeline-slot" in text

    async def test_bottom_nav_style(self, client: AsyncClient):
        """Components CSS includes bottom navigation bar."""
        resp = await client.get("/static/css/components.css")
        text = resp.text
        assert ".bottom-nav" in text
        assert ".nav-item" in text

    async def test_week_selector_for_plan(self, client: AsyncClient):
        """Components CSS includes week-day selector (from Plan screenshot)."""
        resp = await client.get("/static/css/components.css")
        text = resp.text
        assert ".week-selector" in text
        assert ".day-chip" in text

    async def test_status_badges(self, client: AsyncClient):
        """Components CSS includes status badges for all draft/schedule states."""
        resp = await client.get("/static/css/components.css")
        text = resp.text
        for status in ["scheduled", "draft", "published", "failed", "cancelled", "pending"]:
            assert f".badge-{status}" in text

    async def test_onboarding_overlay(self, client: AsyncClient):
        """Components CSS includes onboarding overlay."""
        resp = await client.get("/static/css/components.css")
        text = resp.text
        assert ".onboarding-overlay" in text
        assert ".onboarding-step" in text

    async def test_metric_grid(self, client: AsyncClient):
        """Components CSS includes metric grid for Stats screen."""
        resp = await client.get("/static/css/components.css")
        text = resp.text
        assert ".metric-grid" in text
        assert ".metric-card" in text

    async def test_modal_sheet(self, client: AsyncClient):
        """Components CSS includes modal/sheet for bottom sheets."""
        resp = await client.get("/static/css/components.css")
        text = resp.text
        assert ".modal-overlay" in text
        assert ".modal-sheet" in text


class TestMiniAppAPIIntegration:
    """Verify the JS API client covers all backend endpoints."""

    async def test_api_client_covers_bootstrap(self, client: AsyncClient):
        """API client includes getMe for bootstrap."""
        resp = await client.get("/static/js/api.js")
        assert "getMe" in resp.text
        assert "/me" in resp.text

    async def test_api_client_covers_projects(self, client: AsyncClient):
        """API client includes project CRUD."""
        resp = await client.get("/static/js/api.js")
        text = resp.text
        assert "createProject" in text
        assert "listProjects" in text
        assert "updateProject" in text

    async def test_api_client_covers_drafts(self, client: AsyncClient):
        """API client includes draft lifecycle."""
        resp = await client.get("/static/js/api.js")
        text = resp.text
        assert "createDraft" in text
        assert "listDrafts" in text
        assert "updateDraft" in text
        assert "markReady" in text
        assert "archiveDraft" in text

    async def test_api_client_covers_generation(self, client: AsyncClient):
        """API client includes AI generation endpoints."""
        resp = await client.get("/static/js/api.js")
        text = resp.text
        assert "generateText" in text
        assert "generateImage" in text

    async def test_api_client_covers_publishing(self, client: AsyncClient):
        """API client includes preview and publish."""
        resp = await client.get("/static/js/api.js")
        text = resp.text
        assert "previewDraft" in text
        assert "publishDraft" in text

    async def test_api_client_covers_scheduling(self, client: AsyncClient):
        """API client includes schedule CRUD."""
        resp = await client.get("/static/js/api.js")
        text = resp.text
        assert "scheduleDraft" in text
        assert "listSchedules" in text
        assert "cancelSchedule" in text
        assert "retrySchedule" in text

    async def test_api_client_covers_channel(self, client: AsyncClient):
        """API client includes channel binding."""
        resp = await client.get("/static/js/api.js")
        text = resp.text
        assert "bindChannel" in text
        assert "channelStatus" in text

    async def test_api_client_sends_auth_headers(self, client: AsyncClient):
        """API client sends Telegram auth or dev headers."""
        resp = await client.get("/static/js/api.js")
        text = resp.text
        assert "X-Telegram-Init-Data" in text
        assert "X-Dev-User-Id" in text


class TestMiniAppScreens:
    """Verify each screen module implements required functionality."""

    async def test_home_screen_renders_project_info(self, client: AsyncClient):
        """Home screen shows active project info."""
        resp = await client.get("/static/js/screen-home.js")
        text = resp.text
        assert "Active project" in text
        assert "Quick actions" in text

    async def test_create_screen_has_draft_editor(self, client: AsyncClient):
        """Create screen has draft editing form."""
        resp = await client.get("/static/js/screen-create.js")
        text = resp.text
        assert "draft-title" in text
        assert "draft-text" in text
        assert "gen-text-btn" in text
        assert "gen-image-btn" in text

    async def test_plan_screen_has_week_selector(self, client: AsyncClient):
        """Plan screen has week day selector and timeline."""
        resp = await client.get("/static/js/screen-plan.js")
        text = resp.text
        assert "week-selector" in text
        assert "timeline-slot" in text
        assert "selectDay" in text

    async def test_stats_screen_has_metrics(self, client: AsyncClient):
        """Stats screen shows real metrics from drafts/schedules."""
        resp = await client.get("/static/js/screen-stats.js")
        text = resp.text
        assert "metric-grid" in text
        assert "publishedDrafts" in text
        assert "scheduleSuccessRate" in text

    async def test_channel_screen_has_binding(self, client: AsyncClient):
        """Channel screen includes channel binding flow."""
        resp = await client.get("/static/js/screen-channel.js")
        text = resp.text
        assert "bindChannel" in text
        assert "channel_identifier" in text

    async def test_settings_screen_has_preferences(self, client: AsyncClient):
        """Settings screen includes all preference controls."""
        resp = await client.get("/static/js/screen-settings.js")
        text = resp.text
        assert "defaultTone" in text
        assert "defaultContentType" in text
        assert "formatHashtags" in text
        assert "formatEmoji" in text
        assert "autoSaveDrafts" in text
        assert "defaultScheduleHour" in text

    async def test_onboarding_collects_meaningful_data(self, client: AsyncClient):
        """Onboarding collects project name, preferences, and channel."""
        resp = await client.get("/static/js/onboarding.js")
        text = resp.text
        assert "ob-project-title" in text
        assert "ob-tone" in text
        assert "ob-content-type" in text
        assert "ob-channel-id" in text
