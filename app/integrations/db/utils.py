"""
Shared utilities for the database layer.
"""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC).

    SQLite (and some other backends) strip timezone info from stored
    ``DateTime(timezone=True)`` columns.  This helper re-attaches UTC
    when the value comes back naive.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def ensure_utc_optional(dt: datetime | None) -> datetime | None:
    """Like :func:`ensure_utc` but accepts ``None``."""
    if dt is None:
        return None
    return ensure_utc(dt)
