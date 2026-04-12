"""Telegram Mini App init-data validation.

Validates the ``initData`` string sent by the Telegram Mini App (WebApp)
using the HMAC-SHA256 scheme described in the Telegram Bot API docs:

    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

The module is intentionally self-contained — no FastAPI, no DB, no domain
imports.  Only stdlib + the raw bot token are needed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote


@dataclass(frozen=True)
class TelegramInitData:
    """Parsed and validated init-data from the Telegram Mini App.

    Only the fields needed for user resolution are exposed.
    """

    user_id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    auth_date: int


class InitDataValidationError(Exception):
    """Raised when init-data validation fails."""


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
) -> TelegramInitData:
    """Validate Telegram Mini App init-data and return parsed user info.

    Parameters
    ----------
    init_data:
        The raw ``initData`` query-string from the Mini App.
    bot_token:
        The bot token used to compute the HMAC secret key.
    max_age_seconds:
        Maximum allowed age of the auth_date in seconds.  Defaults to 24h.

    Raises
    ------
    InitDataValidationError
        If the data is missing, malformed, expired, or has an invalid hash.
    """
    if not init_data or not bot_token:
        raise InitDataValidationError("Missing init data or bot token")

    # 1. Parse the query-string pairs
    parsed = parse_qs(init_data, keep_blank_values=True)

    received_hash = parsed.pop("hash", [None])[0]  # type: ignore[list-item]
    if not received_hash:
        raise InitDataValidationError("Missing hash in init data")

    # 2. Build the data-check-string (sorted key=value pairs, \n-separated)
    data_check_pairs: list[str] = []
    for key in sorted(parsed):
        # parse_qs returns list values; take the first for each key
        val = parsed[key][0]
        data_check_pairs.append(f"{key}={val}")

    data_check_string = "\n".join(data_check_pairs)

    # 3. Compute the HMAC-SHA256 secret key
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    # 4. Compute the expected hash
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # 5. Constant-time comparison
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataValidationError("Invalid init data signature")

    # 6. Check auth_date freshness
    auth_date_str = parsed.get("auth_date", [None])[0]  # type: ignore[list-item]
    if not auth_date_str:
        raise InitDataValidationError("Missing auth_date in init data")

    try:
        auth_date = int(auth_date_str)
    except (ValueError, TypeError):
        raise InitDataValidationError("Invalid auth_date format")

    if time.time() - auth_date > max_age_seconds:
        raise InitDataValidationError("Init data has expired")

    # 7. Extract user object
    user_raw = parsed.get("user", [None])[0]  # type: ignore[list-item]
    if not user_raw:
        raise InitDataValidationError("Missing user field in init data")

    try:
        user_data = json.loads(unquote(user_raw))
    except (json.JSONDecodeError, TypeError):
        raise InitDataValidationError("Invalid user JSON in init data")

    user_id = user_data.get("id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise InitDataValidationError("Invalid or missing user id")

    return TelegramInitData(
        user_id=user_id,
        first_name=user_data.get("first_name", ""),
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
        language_code=user_data.get("language_code"),
        auth_date=auth_date,
    )
