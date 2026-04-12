"""Tests for Project domain entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.domain.enums import Platform
from app.domain.project import Project


class TestProjectCreation:
    """Project construction and defaults."""

    def test_minimal_project(self) -> None:
        project = Project(owner_id=1, title="My Channel")
        assert project.owner_id == 1
        assert project.title == "My Channel"
        assert project.id is None
        assert project.description == ""
        assert project.platform == Platform.TELEGRAM
        assert project.platform_channel_id is None
        assert project.is_active is True

    def test_full_project(self) -> None:
        project = Project(
            id=10,
            owner_id=5,
            title="Tech Blog",
            description="A tech channel",
            platform=Platform.VK,
            platform_channel_id="vk_12345",
        )
        assert project.id == 10
        assert project.platform == Platform.VK
        assert project.platform_channel_id == "vk_12345"


class TestProjectValidation:
    """Project invariants."""

    def test_owner_id_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            Project(owner_id=0, title="Test")

    def test_title_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            Project(owner_id=1, title="")

    def test_title_stripped(self) -> None:
        project = Project(owner_id=1, title="  My Channel  ")
        assert project.title == "My Channel"

    def test_title_max_length(self) -> None:
        with pytest.raises(PydanticValidationError):
            Project(owner_id=1, title="x" * 201)

    def test_description_stripped(self) -> None:
        project = Project(owner_id=1, title="Test", description="  desc  ")
        assert project.description == "desc"

    def test_description_max_length(self) -> None:
        with pytest.raises(PydanticValidationError):
            Project(owner_id=1, title="Test", description="x" * 2001)


class TestProjectImmutability:
    """Project model is frozen."""

    def test_cannot_mutate(self) -> None:
        project = Project(owner_id=1, title="Test")
        with pytest.raises(PydanticValidationError):
            project.title = "New"  # type: ignore[misc]


class TestProjectDomainMethods:
    """Project rename, deactivate, activate, link_channel."""

    def test_rename(self) -> None:
        project = Project(owner_id=1, title="Old Name")
        renamed = project.rename("New Name")
        assert renamed.title == "New Name"
        assert project.title == "Old Name"  # original unchanged

    def test_rename_strips(self) -> None:
        project = Project(owner_id=1, title="Old")
        renamed = project.rename("  New  ")
        assert renamed.title == "New"

    def test_deactivate(self) -> None:
        project = Project(owner_id=1, title="Test")
        deactivated = project.deactivate()
        assert deactivated.is_active is False
        assert project.is_active is True

    def test_activate(self) -> None:
        project = Project(owner_id=1, title="Test", is_active=False)
        activated = project.activate()
        assert activated.is_active is True

    def test_link_channel(self) -> None:
        project = Project(owner_id=1, title="Test")
        linked = project.link_channel("@mychannel")
        assert linked.platform_channel_id == "@mychannel"
        assert project.platform_channel_id is None

    def test_rename_updates_timestamp(self) -> None:
        before = datetime.now(UTC)
        project = Project(
            owner_id=1, title="Test", updated_at=datetime(2020, 1, 1, tzinfo=UTC)
        )
        renamed = project.rename("New")
        assert renamed.updated_at >= before
