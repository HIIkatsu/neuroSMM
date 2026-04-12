"""
NeuroSMM V2 — Domain Layer.

Pure domain entities and value objects with no I/O dependencies.

Public re-exports so downstream code can write::

    from app.domain import User, Project, Draft, ScheduledPost
"""

from app.domain.draft import Draft
from app.domain.enums import (
    ContentType,
    DraftStatus,
    GenerationStatus,
    GenerationType,
    Platform,
    ScheduleStatus,
    Tone,
)
from app.domain.generation import GenerationRequest, GenerationResult
from app.domain.project import Project
from app.domain.schedule import ScheduledPost
from app.domain.user import User

__all__ = [
    # entities
    "Draft",
    "Project",
    "ScheduledPost",
    "User",
    # value objects
    "GenerationRequest",
    "GenerationResult",
    # enums
    "ContentType",
    "DraftStatus",
    "GenerationStatus",
    "GenerationType",
    "Platform",
    "ScheduleStatus",
    "Tone",
]
