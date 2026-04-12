"""Tests for Telegram Mini App init-data validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import quote, urlencode

import pytest

from app.integrations.telegram.auth import (
    InitDataValidationError,
    TelegramInitData,
    validate_init_data,
)

BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def _build_init_data(
    *,
    bot_token: str = BOT_TOKEN,
    user_id: int = 12345,
    first_name: str = "John",
    last_name: str | None = "Doe",
    username: str | None = "johndoe",
    language_code: str | None = "en",
    auth_date: int | None = None,
    tamper_hash: bool = False,
    omit_hash: bool = False,
    omit_user: bool = False,
    omit_auth_date: bool = False,
) -> str:
    """Build a valid (or intentionally invalid) Telegram init-data string."""
    if auth_date is None:
        auth_date = int(time.time())

    user_obj: dict[str, object] = {"id": user_id, "first_name": first_name}
    if last_name:
        user_obj["last_name"] = last_name
    if username:
        user_obj["username"] = username
    if language_code:
        user_obj["language_code"] = language_code

    params: dict[str, str] = {}
    if not omit_auth_date:
        params["auth_date"] = str(auth_date)
    if not omit_user:
        params["user"] = json.dumps(user_obj, separators=(",", ":"))

    # Build data-check-string
    data_check_pairs = [f"{k}={params[k]}" for k in sorted(params)]
    data_check_string = "\n".join(data_check_pairs)

    # Compute HMAC
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if tamper_hash:
        computed_hash = "a" * 64

    if not omit_hash:
        params["hash"] = computed_hash

    return urlencode(params, quote_via=quote)


class TestValidateInitData:
    """Tests for the validate_init_data function."""

    def test_valid_init_data_returns_parsed_result(self) -> None:
        """Valid init-data should parse correctly."""
        init_data = _build_init_data()
        result = validate_init_data(init_data, BOT_TOKEN)

        assert isinstance(result, TelegramInitData)
        assert result.user_id == 12345
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.username == "johndoe"
        assert result.language_code == "en"

    def test_valid_init_data_auth_date_present(self) -> None:
        """auth_date should be captured in the result."""
        auth_date = int(time.time()) - 100
        init_data = _build_init_data(auth_date=auth_date)
        result = validate_init_data(init_data, BOT_TOKEN)

        assert result.auth_date == auth_date

    def test_invalid_hash_raises_error(self) -> None:
        """Tampered hash should cause validation failure."""
        init_data = _build_init_data(tamper_hash=True)

        with pytest.raises(InitDataValidationError, match="Invalid init data signature"):
            validate_init_data(init_data, BOT_TOKEN)

    def test_missing_hash_raises_error(self) -> None:
        """Missing hash should cause validation failure."""
        init_data = _build_init_data(omit_hash=True)

        with pytest.raises(InitDataValidationError, match="Missing hash"):
            validate_init_data(init_data, BOT_TOKEN)

    def test_missing_user_raises_error(self) -> None:
        """Missing user field should cause validation failure."""
        init_data = _build_init_data(omit_user=True)

        with pytest.raises(InitDataValidationError, match="Missing user"):
            validate_init_data(init_data, BOT_TOKEN)

    def test_missing_auth_date_raises_error(self) -> None:
        """Missing auth_date should cause validation failure."""
        init_data = _build_init_data(omit_auth_date=True)

        with pytest.raises(InitDataValidationError, match="Missing auth_date"):
            validate_init_data(init_data, BOT_TOKEN)

    def test_expired_init_data_raises_error(self) -> None:
        """Expired auth_date should cause validation failure."""
        old_date = int(time.time()) - 100_000  # well past 24h
        init_data = _build_init_data(auth_date=old_date)

        with pytest.raises(InitDataValidationError, match="expired"):
            validate_init_data(init_data, BOT_TOKEN)

    def test_wrong_bot_token_raises_error(self) -> None:
        """Using the wrong bot token should cause signature mismatch."""
        init_data = _build_init_data(bot_token=BOT_TOKEN)

        with pytest.raises(InitDataValidationError, match="Invalid init data signature"):
            validate_init_data(init_data, "999999:WRONG-TOKEN")

    def test_empty_init_data_raises_error(self) -> None:
        """Empty init-data string should raise."""
        with pytest.raises(InitDataValidationError, match="Missing init data"):
            validate_init_data("", BOT_TOKEN)

    def test_empty_bot_token_raises_error(self) -> None:
        """Empty bot token should raise."""
        init_data = _build_init_data()
        with pytest.raises(InitDataValidationError, match="Missing init data"):
            validate_init_data(init_data, "")

    def test_user_with_minimal_fields(self) -> None:
        """User with only required fields should parse correctly."""
        init_data = _build_init_data(
            last_name=None, username=None, language_code=None
        )
        result = validate_init_data(init_data, BOT_TOKEN)

        assert result.user_id == 12345
        assert result.first_name == "John"
        assert result.last_name is None
        assert result.username is None
        assert result.language_code is None

    def test_custom_max_age(self) -> None:
        """Custom max_age_seconds should be respected."""
        old_date = int(time.time()) - 60  # 60 seconds ago
        init_data = _build_init_data(auth_date=old_date)

        # Should pass with 120s max age
        result = validate_init_data(init_data, BOT_TOKEN, max_age_seconds=120)
        assert result.user_id == 12345

        # Should fail with 30s max age
        with pytest.raises(InitDataValidationError, match="expired"):
            validate_init_data(init_data, BOT_TOKEN, max_age_seconds=30)
