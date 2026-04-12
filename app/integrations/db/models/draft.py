"""
ORM model for the Draft entity.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.integrations.db.base import Base


class DraftORM(Base):
    """SQLAlchemy ORM model for the ``drafts`` table."""

    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    text_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="text"
    )
    tone: Mapped[str] = mapped_column(String(50), nullable=False, default="neutral")
    topic: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<DraftORM id={self.id} status={self.status!r}>"
