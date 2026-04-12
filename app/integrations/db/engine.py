"""
Async SQLAlchemy engine and session factory.

Provides factory functions for creating the async engine and session maker.
No hidden global state — callers receive explicit objects they manage.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def get_async_engine(
    url: str,
    *,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> AsyncEngine:
    """Create an :class:`AsyncEngine` from a database URL.

    Parameters
    ----------
    url:
        SQLAlchemy-compatible async database URL
        (e.g. ``sqlite+aiosqlite:///...`` or ``postgresql+asyncpg://...``).
    echo:
        When *True*, log all emitted SQL statements.
    pool_size:
        Number of persistent connections in the pool.
    max_overflow:
        Extra connections allowed above *pool_size*.
    """
    # SQLite doesn't support pool_size / max_overflow
    connect_args: dict[str, object] = {}
    kwargs: dict[str, object] = {"echo": echo}

    if url.startswith("sqlite"):
        kwargs["pool_size"] = 0
        kwargs["max_overflow"] = 0
        kwargs["pool_pre_ping"] = False
        connect_args["check_same_thread"] = False
        kwargs["connect_args"] = connect_args
    else:
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = max_overflow
        kwargs["pool_pre_ping"] = True

    return create_async_engine(url, **kwargs)


def get_async_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return an ``async_sessionmaker`` bound to the given engine.

    The session factory creates new :class:`AsyncSession` instances — one per
    unit-of-work — with ``expire_on_commit=False`` so that attributes stay
    accessible after commit.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
