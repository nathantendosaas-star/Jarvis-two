"""Setting model — key-value store for application preferences."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, default="")
