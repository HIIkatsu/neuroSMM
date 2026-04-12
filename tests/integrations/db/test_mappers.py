"""
Tests for ORM ↔ domain mappers — explicit mapping correctness,
edge cases, and invalid-value handling.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.draft import Draft
from app.domain.enums import (
    ContentType,
    DraftStatus,
    Platform,
    ScheduleStatus,
    Tone,
)
from app.domain.project import Project
from app.domain.schedule import ScheduledPost
from app.domain.user import User
from app.integrations.db.mappers.draft import draft_to_domain, draft_to_orm
from app.integrations.db.mappers.project import project_to_domain, project_to_orm
from app.integrations.db.mappers.scheduled_post import (
    scheduled_post_to_domain,
    scheduled_post_to_orm,
)
from app.integrations.db.mappers.user import user_to_domain, user_to_orm
from app.integrations.db.models.draft import DraftORM
from app.integrations.db.models.project import ProjectORM
from app.integrations.db.models.scheduled_post import ScheduledPostORM
from app.integrations.db.models.user import UserORM

NOW = datetime.now(UTC)


# ── User mapper ────────────────────────────────────────────────────────


class TestUserMapper:
    def test_to_orm_and_back(self) -> None:
        user = User(
            id=1,
            telegram_id=12345,
            username="alice",
            first_name="Alice",
            last_name="Smith",
            language_code="en",
            is_active=True,
            created_at=NOW,
            updated_at=NOW,
        )
        orm = user_to_orm(user)
        assert isinstance(orm, UserORM)
        assert orm.telegram_id == 12345
        assert orm.id == 1

        back = user_to_domain(orm)
        assert isinstance(back, User)
        assert back.telegram_id == 12345
        assert back.username == "alice"

    def test_to_orm_without_id(self) -> None:
        user = User(telegram_id=999, first_name="NoID", created_at=NOW, updated_at=NOW)
        orm = user_to_orm(user)
        # When domain id is None, ORM id should not be explicitly set
        # (autoincrement handles it)
        assert orm.telegram_id == 999

    def test_optional_fields_none(self) -> None:
        user = User(telegram_id=1, first_name="Min", created_at=NOW, updated_at=NOW)
        orm = user_to_orm(user)
        back = user_to_domain(orm)
        assert back.username is None
        assert back.last_name is None
        assert back.language_code is None

    def test_from_orm_with_invalid_enum_value(self) -> None:
        """ORM row with garbage values should still map (enums are strings)."""
        # User has no enum fields, but verify round-trip is clean
        orm = UserORM()
        orm.id = 1
        orm.telegram_id = 42
        orm.username = None
        orm.first_name = ""
        orm.last_name = None
        orm.language_code = None
        orm.is_active = True
        orm.created_at = NOW
        orm.updated_at = NOW
        domain = user_to_domain(orm)
        assert domain.id == 1


# ── Project mapper ─────────────────────────────────────────────────────


class TestProjectMapper:
    def test_to_orm_and_back(self) -> None:
        proj = Project(
            id=10,
            owner_id=1,
            title="My Channel",
            description="Desc",
            platform=Platform.VK,
            platform_channel_id="vk-1",
            is_active=True,
            created_at=NOW,
            updated_at=NOW,
        )
        orm = project_to_orm(proj)
        assert isinstance(orm, ProjectORM)
        assert orm.platform == "vk"
        assert orm.id == 10

        back = project_to_domain(orm)
        assert isinstance(back, Project)
        assert back.platform == Platform.VK
        assert back.platform_channel_id == "vk-1"

    def test_platform_enum_stored_as_string(self) -> None:
        proj = Project(
            owner_id=1, title="T", platform=Platform.TELEGRAM,
            created_at=NOW, updated_at=NOW,
        )
        orm = project_to_orm(proj)
        assert orm.platform == "telegram"

    def test_from_orm_invalid_platform_raises(self) -> None:
        orm = ProjectORM()
        orm.id = 1
        orm.owner_id = 1
        orm.title = "X"
        orm.description = ""
        orm.platform = "invalid_platform"
        orm.platform_channel_id = None
        orm.is_active = True
        orm.created_at = NOW
        orm.updated_at = NOW
        with pytest.raises(ValueError):
            project_to_domain(orm)


# ── Draft mapper ───────────────────────────────────────────────────────


class TestDraftMapper:
    def test_to_orm_and_back(self) -> None:
        draft = Draft(
            id=5,
            project_id=10,
            author_id=1,
            title="Hello",
            text_content="World",
            content_type=ContentType.TEXT,
            tone=Tone.CASUAL,
            topic="greetings",
            status=DraftStatus.READY,
            created_at=NOW,
            updated_at=NOW,
        )
        orm = draft_to_orm(draft)
        assert isinstance(orm, DraftORM)
        assert orm.status == "ready"
        assert orm.tone == "casual"
        assert orm.content_type == "text"

        back = draft_to_domain(orm)
        assert isinstance(back, Draft)
        assert back.status == DraftStatus.READY
        assert back.tone == Tone.CASUAL

    def test_all_enum_fields_stored_as_strings(self) -> None:
        draft = Draft(
            project_id=1,
            author_id=1,
            text_content="t",
            content_type=ContentType.TEXT_AND_IMAGE,
            tone=Tone.HUMOROUS,
            status=DraftStatus.ARCHIVED,
            image_url="http://img",
            created_at=NOW,
            updated_at=NOW,
        )
        orm = draft_to_orm(draft)
        assert orm.content_type == "text_and_image"
        assert orm.tone == "humorous"
        assert orm.status == "archived"

    def test_from_orm_invalid_status_raises(self) -> None:
        orm = DraftORM()
        orm.id = 1
        orm.project_id = 1
        orm.author_id = 1
        orm.title = ""
        orm.text_content = ""
        orm.image_url = None
        orm.content_type = "text"
        orm.tone = "neutral"
        orm.topic = ""
        orm.status = "invalid_status"
        orm.created_at = NOW
        orm.updated_at = NOW
        with pytest.raises(ValueError):
            draft_to_domain(orm)

    def test_from_orm_invalid_tone_raises(self) -> None:
        orm = DraftORM()
        orm.id = 1
        orm.project_id = 1
        orm.author_id = 1
        orm.title = ""
        orm.text_content = ""
        orm.image_url = None
        orm.content_type = "text"
        orm.tone = "bad_tone"
        orm.topic = ""
        orm.status = "draft"
        orm.created_at = NOW
        orm.updated_at = NOW
        with pytest.raises(ValueError):
            draft_to_domain(orm)


# ── ScheduledPost mapper ──────────────────────────────────────────────


class TestScheduledPostMapper:
    def test_to_orm_and_back(self) -> None:
        post = ScheduledPost(
            id=3,
            draft_id=5,
            project_id=10,
            publish_at=NOW,
            status=ScheduleStatus.FAILED,
            failure_reason="timeout",
            published_at=None,
            created_at=NOW,
            updated_at=NOW,
        )
        orm = scheduled_post_to_orm(post)
        assert isinstance(orm, ScheduledPostORM)
        assert orm.status == "failed"
        assert orm.failure_reason == "timeout"

        back = scheduled_post_to_domain(orm)
        assert isinstance(back, ScheduledPost)
        assert back.status == ScheduleStatus.FAILED
        assert back.failure_reason == "timeout"

    def test_status_stored_as_string(self) -> None:
        post = ScheduledPost(
            draft_id=1,
            project_id=1,
            publish_at=NOW,
            status=ScheduleStatus.CANCELLED,
            created_at=NOW,
            updated_at=NOW,
        )
        orm = scheduled_post_to_orm(post)
        assert orm.status == "cancelled"

    def test_from_orm_invalid_status_raises(self) -> None:
        orm = ScheduledPostORM()
        orm.id = 1
        orm.draft_id = 1
        orm.project_id = 1
        orm.publish_at = NOW
        orm.status = "bogus"
        orm.failure_reason = None
        orm.published_at = None
        orm.created_at = NOW
        orm.updated_at = NOW
        with pytest.raises(ValueError):
            scheduled_post_to_domain(orm)

    def test_published_at_nullable(self) -> None:
        post = ScheduledPost(
            draft_id=1,
            project_id=1,
            publish_at=NOW,
            published_at=None,
            created_at=NOW,
            updated_at=NOW,
        )
        orm = scheduled_post_to_orm(post)
        assert orm.published_at is None

        back = scheduled_post_to_domain(orm)
        assert back.published_at is None
