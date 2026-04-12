"""Tests for User domain entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.domain.user import User


class TestUserCreation:
    """User entity construction and defaults."""

    def test_minimal_user(self) -> None:
        user = User(telegram_id=123456)
        assert user.telegram_id == 123456
        assert user.id is None
        assert user.username is None
        assert user.first_name == ""
        assert user.last_name is None
        assert user.language_code is None
        assert user.is_active is True
        assert user.created_at.tzinfo is not None
        assert user.updated_at.tzinfo is not None

    def test_full_user(self) -> None:
        user = User(
            id=1,
            telegram_id=999,
            username="alice",
            first_name="Alice",
            last_name="Smith",
            language_code="en",
        )
        assert user.id == 1
        assert user.telegram_id == 999
        assert user.username == "alice"
        assert user.first_name == "Alice"
        assert user.last_name == "Smith"
        assert user.language_code == "en"


class TestUserValidation:
    """User invariants enforcement."""

    def test_telegram_id_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            User(telegram_id=0)

    def test_telegram_id_negative_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            User(telegram_id=-1)

    def test_telegram_id_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            User()  # type: ignore[call-arg]

    def test_username_stripped(self) -> None:
        user = User(telegram_id=1, username="  alice  ")
        assert user.username == "alice"

    def test_username_at_sign_removed(self) -> None:
        user = User(telegram_id=1, username="@alice")
        assert user.username == "alice"

    def test_empty_username_becomes_none(self) -> None:
        user = User(telegram_id=1, username="  ")
        assert user.username is None

    def test_at_only_username_becomes_none(self) -> None:
        user = User(telegram_id=1, username="@")
        assert user.username is None

    def test_first_name_stripped(self) -> None:
        user = User(telegram_id=1, first_name="  Alice  ")
        assert user.first_name == "Alice"


class TestUserImmutability:
    """User model is frozen / immutable."""

    def test_cannot_mutate_fields(self) -> None:
        user = User(telegram_id=1)
        with pytest.raises(PydanticValidationError):
            user.telegram_id = 2  # type: ignore[misc]


class TestUserDisplayName:
    """Display name derivation."""

    def test_username_preferred(self) -> None:
        user = User(telegram_id=1, username="alice", first_name="Alice")
        assert user.display_name == "@alice"

    def test_first_name_fallback(self) -> None:
        user = User(telegram_id=1, first_name="Alice")
        assert user.display_name == "Alice"

    def test_full_name_fallback(self) -> None:
        user = User(telegram_id=1, first_name="Alice", last_name="Smith")
        assert user.display_name == "Alice Smith"

    def test_unknown_fallback(self) -> None:
        user = User(telegram_id=1, first_name="")
        assert user.display_name == "Unknown"


class TestUserDomainMethods:
    """Deactivation, activation, and profile update methods."""

    def test_deactivate(self) -> None:
        user = User(telegram_id=1)
        deactivated = user.deactivate()
        assert deactivated.is_active is False
        assert user.is_active is True  # original unchanged

    def test_activate(self) -> None:
        user = User(telegram_id=1, is_active=False)
        activated = user.activate()
        assert activated.is_active is True

    def test_with_updated_profile(self) -> None:
        user = User(telegram_id=1, first_name="Old")
        updated = user.with_updated_profile(first_name="New", username="newname")
        assert updated.first_name == "New"
        assert updated.username == "newname"
        assert user.first_name == "Old"  # original unchanged

    def test_updated_profile_preserves_unset_fields(self) -> None:
        user = User(telegram_id=1, first_name="Alice", language_code="en")
        updated = user.with_updated_profile(first_name="Bob")
        assert updated.first_name == "Bob"
        assert updated.language_code == "en"  # preserved

    def test_deactivate_updates_timestamp(self) -> None:
        before = datetime.now(UTC)
        user = User(telegram_id=1, updated_at=datetime(2020, 1, 1, tzinfo=UTC))
        deactivated = user.deactivate()
        assert deactivated.updated_at >= before
