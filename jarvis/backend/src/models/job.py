"""Job model — tracks a single subprocess execution (e.g. a lead-scraping script)."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    script_path: Mapped[str] = mapped_column(String(512))
    """Workspace-relative path to the script, e.g. 'backend/scripts/lead_scraper.py'"""

    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    """Workspace-relative path to the output file (CSV). Set by the script via the callback."""

    status: Mapped[str] = mapped_column(String(32), default="queued")
    """queued → running → done | failed"""

    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """OS process ID of the launched subprocess."""

    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Process exit code. 0 = success."""

    stdout_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Last 4000 chars of subprocess stdout."""

    stderr_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Last 4000 chars of subprocess stderr."""

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Human-readable failure reason (timeout, path violation, etc.)."""

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
