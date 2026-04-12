"""Tests for domain enumerations."""

from __future__ import annotations

from app.domain.enums import (
    ContentType,
    DraftStatus,
    GenerationStatus,
    GenerationType,
    Platform,
    ScheduleStatus,
    Tone,
)


class TestDraftStatus:
    """DraftStatus enum values and membership."""

    def test_values(self) -> None:
        assert DraftStatus.DRAFT == "draft"
        assert DraftStatus.READY == "ready"
        assert DraftStatus.PUBLISHED == "published"
        assert DraftStatus.ARCHIVED == "archived"

    def test_member_count(self) -> None:
        assert len(DraftStatus) == 4

    def test_is_str(self) -> None:
        assert isinstance(DraftStatus.DRAFT, str)


class TestScheduleStatus:
    """ScheduleStatus enum values."""

    def test_values(self) -> None:
        assert ScheduleStatus.PENDING == "pending"
        assert ScheduleStatus.PUBLISHED == "published"
        assert ScheduleStatus.FAILED == "failed"
        assert ScheduleStatus.CANCELLED == "cancelled"

    def test_member_count(self) -> None:
        assert len(ScheduleStatus) == 4


class TestContentType:
    """ContentType enum values."""

    def test_values(self) -> None:
        assert ContentType.TEXT == "text"
        assert ContentType.IMAGE == "image"
        assert ContentType.TEXT_AND_IMAGE == "text_and_image"

    def test_member_count(self) -> None:
        assert len(ContentType) == 3


class TestTone:
    """Tone enum values."""

    def test_values(self) -> None:
        assert Tone.NEUTRAL == "neutral"
        assert Tone.FORMAL == "formal"
        assert Tone.CASUAL == "casual"
        assert Tone.HUMOROUS == "humorous"
        assert Tone.PROMOTIONAL == "promotional"

    def test_member_count(self) -> None:
        assert len(Tone) == 5


class TestPlatform:
    """Platform enum values."""

    def test_values(self) -> None:
        assert Platform.TELEGRAM == "telegram"
        assert Platform.VK == "vk"

    def test_member_count(self) -> None:
        assert len(Platform) == 2


class TestGenerationStatus:
    """GenerationStatus enum values."""

    def test_values(self) -> None:
        assert GenerationStatus.PENDING == "pending"
        assert GenerationStatus.IN_PROGRESS == "in_progress"
        assert GenerationStatus.COMPLETED == "completed"
        assert GenerationStatus.FAILED == "failed"

    def test_member_count(self) -> None:
        assert len(GenerationStatus) == 4


class TestGenerationType:
    """GenerationType enum values."""

    def test_values(self) -> None:
        assert GenerationType.TEXT == "text"
        assert GenerationType.IMAGE == "image"

    def test_member_count(self) -> None:
        assert len(GenerationType) == 2
