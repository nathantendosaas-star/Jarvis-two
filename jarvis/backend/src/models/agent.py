"""Agent model — tracks persistent AI agent workforce entities and their state."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False, default="General Agent")
    avatar: Mapped[str] = mapped_column(String(10), nullable=False, default="🤖")

    # Lifecycle state
    status: Mapped[str] = mapped_column(String(50), default="idle")        # idle | working | paused | offline
    current_task: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")   # high | medium | low

    # Resource allocations (UI-exposed sliders)
    cpu_allocation: Mapped[int] = mapped_column(Integer, default=50)       # percent 0-100
    memory_allocation: Mapped[int] = mapped_column(Integer, default=128)   # MB 0-512

    # JSON-encoded lists (stored as Text for SQLite compatibility)
    capabilities: Mapped[str | None] = mapped_column(Text, default="[]")   # JSON array of strings
    tools: Mapped[str | None] = mapped_column(Text, default="[]")          # JSON array of strings
    activity: Mapped[str | None] = mapped_column(Text, default="[]")       # JSON array of recent log lines

    # Metrics
    performance: Mapped[int] = mapped_column(Integer, default=100)         # success rate %, 0-100

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
