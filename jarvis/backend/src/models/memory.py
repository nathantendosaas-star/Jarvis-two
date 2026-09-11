"""Memory model — structured context, summaries, and pinned notes."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), default="")
    content: Mapped[str | None] = mapped_column(Text, default="")
    importance: Mapped[int | None] = mapped_column(Integer, default=5)  # 1-10
    memory_type: Mapped[str] = mapped_column(String(32), default="project", index=True)
    scope: Mapped[str] = mapped_column(String(64), default="project", index=True)
    lineage: Mapped[str] = mapped_column(Text, default="{}")
    retrieval_metadata: Mapped[str] = mapped_column(Text, default="{}")
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0)
    last_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="memories")
