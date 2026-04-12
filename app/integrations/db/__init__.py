"""
NeuroSMM V2 — Database Integration Layer.

Async SQLAlchemy setup, ORM models, mappers, and repository implementations.

Public re-exports::

    from app.integrations.db import get_async_engine, get_async_session_factory
    from app.integrations.db import UserRepository, ProjectRepository, ...
"""

from app.integrations.db.engine import get_async_engine, get_async_session_factory
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.db.repositories.scheduled_post import ScheduledPostRepository
from app.integrations.db.repositories.user import UserRepository

__all__ = [
    "DraftRepository",
    "ProjectRepository",
    "ScheduledPostRepository",
    "UserRepository",
    "get_async_engine",
    "get_async_session_factory",
]
