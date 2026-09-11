"""Application configuration loaded from environment variables."""

from pathlib import Path
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration object. Values sourced from .env or OS environment."""

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
    JARVIS_PASSWORD: str = os.getenv("JARVIS_PASSWORD", "jarvis")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///.storage/jarvis.db")
    STORAGE_DIR: Path = Path(os.getenv("STORAGE_DIR", ".storage/uploads"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "jarvis-secret-key-change-in-production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    APP_URL: str = os.getenv("APP_URL", "http://localhost:3000")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB

    def __init__(self):
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        Path(".storage").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
