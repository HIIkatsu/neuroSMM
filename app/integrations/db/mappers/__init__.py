"""
Explicit mappers between ORM models and domain entities.

Each mapper pair (``to_domain`` / ``to_orm``) is a plain function that
converts between the two representations.  This keeps ORM types out of
the domain layer and makes the mapping fully testable.
"""

from app.integrations.db.mappers.draft import draft_to_domain, draft_to_orm
from app.integrations.db.mappers.project import project_to_domain, project_to_orm
from app.integrations.db.mappers.scheduled_post import (
    scheduled_post_to_domain,
    scheduled_post_to_orm,
)
from app.integrations.db.mappers.user import user_to_domain, user_to_orm

__all__ = [
    "draft_to_domain",
    "draft_to_orm",
    "project_to_domain",
    "project_to_orm",
    "scheduled_post_to_domain",
    "scheduled_post_to_orm",
    "user_to_domain",
    "user_to_orm",
]
