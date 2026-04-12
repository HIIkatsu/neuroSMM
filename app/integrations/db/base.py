"""
SQLAlchemy declarative base and shared metadata.

All ORM models inherit from :class:`Base`.  The single :data:`metadata` instance
is shared with Alembic for migration auto-generation.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application-wide declarative base for all ORM models."""
